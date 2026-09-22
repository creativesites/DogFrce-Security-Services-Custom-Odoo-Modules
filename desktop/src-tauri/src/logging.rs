//! Rotating local log file: the only record of what happened on a machine
//! nobody can watch. A double-clicked Windows .exe has no console, so
//! stdout alone goes nowhere.
//!
//! Nothing secret is logged anywhere in this app (errors.rs never carries a
//! cookie, token or password); this file inherits that rule.

use std::path::PathBuf;
use tracing_appender::rolling::{Builder, Rotation};
use tracing_subscriber::{fmt, layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

const KEEP_DAYS: usize = 7;

/// Returns the directory being written to, or `None` if only stdout is
/// available (the directory couldn't be created -- logging must never stop
/// the app from starting).
pub fn init(log_dir: Option<PathBuf>) -> Option<PathBuf> {
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"));

    let file = log_dir.and_then(|dir| {
        std::fs::create_dir_all(&dir).ok()?;
        let appender = Builder::new()
            .rotation(Rotation::DAILY)
            .filename_prefix("deployguard")
            .filename_suffix("log")
            .max_log_files(KEEP_DAYS)
            .build(&dir)
            .ok()?;
        Some((dir, appender))
    });

    // Blocking writes on purpose: this app logs a handful of lines a minute,
    // and a non-blocking writer's buffer is lost when a panic aborts the
    // process (release builds use panic = "abort") -- exactly the line
    // that would matter most.
    let (dir, file_layer) = match file {
        Some((dir, appender)) => (Some(dir), Some(fmt::layer().with_ansi(false).with_writer(appender))),
        None => (None, None),
    };

    let _ = tracing_subscriber::registry()
        .with(filter)
        .with(fmt::layer())
        .with(file_layer)
        .try_init();

    let default_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        tracing::error!(panic = %info, "the app crashed");
        default_hook(info);
    }));

    dir
}

#[cfg(test)]
mod tests {
    use super::init;

    // One test only: the global subscriber can be installed once per process.
    #[test]
    fn writes_log_lines_to_a_file_in_the_given_folder() {
        let dir = std::env::temp_dir().join(format!("dg-log-test-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);

        let used = init(Some(dir.clone()));
        assert_eq!(used.as_deref(), Some(dir.as_path()));

        tracing::warn!("marker-line-for-test");
        let contents: String = std::fs::read_dir(&dir)
            .expect("log folder was created")
            .filter_map(|e| std::fs::read_to_string(e.ok()?.path()).ok())
            .collect();
        assert!(contents.contains("marker-line-for-test"), "log file didn't receive the line");
        assert!(!contents.contains("\u{1b}["), "ANSI colour codes leaked into the file");

        let _ = std::fs::remove_dir_all(&dir);
    }
}
