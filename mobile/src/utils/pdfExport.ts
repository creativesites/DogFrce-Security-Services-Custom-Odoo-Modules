import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import { AttendanceRecord, SitePostingSheetResponse, HistoryBatch } from '../api/supervisor';

export const generatePostingSheetPDF = async (
  sheetData: SitePostingSheetResponse,
  siteName: string
): Promise<void> => {
  const dateStr = sheetData.date || new Date().toISOString().split('T')[0];
  const slots = sheetData.slots || [];
  
  const total = slots.length;
  const present = slots.filter((s) => s.manual_presence === 'present').length;
  const absent = slots.filter((s) => s.manual_presence === 'absent').length;
  const awol = slots.filter((s) => s.manual_presence === 'awol').length;
  const rate = total > 0 ? Math.round((present / total) * 100) : 0;

  const rowsHtml = slots
    .map(
      (slot, idx) => `
    <tr style="background-color: ${idx % 2 === 0 ? '#ffffff' : '#f8fafc'};">
      <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">${slot.guard.name}</td>
      <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0; color: #64748b;">${slot.post || 'Unassigned'}</td>
      <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0; color: #64748b;">${slot.shift || 'N/A'}</td>
      <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0;">
        <span style="
          padding: 4px 8px;
          border-radius: 6px;
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          background-color: ${
            slot.manual_presence === 'present'
              ? '#d1fae5; color: #065f46;'
              : slot.manual_presence === 'absent'
              ? '#fee2e2; color: #991b1b;'
              : slot.manual_presence === 'awol'
              ? '#ffedd5; color: #9a3412;'
              : '#f1f5f9; color: #475569;'
          }
        ">
          ${slot.manual_presence.replace('_', ' ')}
        </span>
      </td>
      <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">
        ${slot.check_in ? new Date(slot.check_in).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--'}
      </td>
    </tr>
  `
    )
    .join('');

  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Posting Sheet - ${siteName}</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 32px; color: #0f172a; }
          .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0f172a; padding-bottom: 16px; margin-bottom: 24px; }
          .title { font-size: 24px; font-weight: 800; color: #0f172a; margin: 0; }
          .subtitle { font-size: 14px; color: #64748b; margin-top: 4px; }
          .badge { background: #1e293b; color: #ffffff; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 700; letter-spacing: 0.5px; }
          .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 28px; }
          .stat-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 16px; }
          .stat-label { font-size: 11px; text-transform: uppercase; font-weight: 700; color: #64748b; }
          .stat-value { font-size: 22px; font-weight: 800; color: #0f172a; margin-top: 4px; }
          table { width: 100%; border-collapse: collapse; text-align: left; }
          th { background: #0f172a; color: #ffffff; font-size: 11px; text-transform: uppercase; font-weight: 700; padding: 10px 12px; }
          .footer { margin-top: 40px; text-align: center; font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 16px; }
        </style>
      </head>
      <body>
        <div class="header">
          <div>
            <h1 class="title">${siteName}</h1>
            <div class="subtitle">Daily Posting Sheet Report • Date: ${dateStr}</div>
          </div>
          <div class="badge">DogForce Security</div>
        </div>

        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">Total Scheduled</div>
            <div class="stat-value">${total}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Present</div>
            <div class="stat-value" style="color: #059669;">${present}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Absent / AWOL</div>
            <div class="stat-value" style="color: #dc2626;">${absent + awol}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Attendance Rate</div>
            <div class="stat-value" style="color: #2563eb;">${rate}%</div>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th>Guard Name</th>
              <th>Post</th>
              <th>Shift</th>
              <th>Status</th>
              <th>Check In</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml || '<tr><td colspan="5" style="text-align: center; padding: 20px;">No guard attendance records found.</td></tr>'}
          </tbody>
        </table>

        <div class="footer">
          Generated automatically via DogForce DeployGuard Mobile Suite • ${new Date().toLocaleString()}
        </div>
      </body>
    </html>
  `;

  try {
    const { uri } = await Print.printToFileAsync({ html });
    if (await Sharing.isAvailableAsync()) {
      await Sharing.shareAsync(uri, { UTI: '.pdf', mimeType: 'application/pdf' });
    }
  } catch (err) {
    console.error('PDF Generation Error:', err);
    throw err;
  }
};

export const generateHistoryReportPDF = async (batches: HistoryBatch[]): Promise<void> => {
  const rowsHtml = batches
    .map(
      (b, idx) => `
    <tr style="background-color: ${idx % 2 === 0 ? '#ffffff' : '#f8fafc'};">
      <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">${b.date}</td>
      <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0; color: #64748b;">${b.site?.name || 'All Sites'}</td>
      <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0; text-transform: uppercase; font-weight: 700; font-size: 11px;">${b.state}</td>
      <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0; font-weight: 700; color: #059669;">${b.summary.present}/${b.summary.total}</td>
      <td style="padding: 10px 12px; border-bottom: 1px solid #e2e8f0; font-weight: 800; color: #2563eb;">${b.summary.attendance_rate}%</td>
    </tr>
  `
    )
    .join('');

  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Attendance History Summary</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 32px; color: #0f172a; }
          .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0f172a; padding-bottom: 16px; margin-bottom: 24px; }
          .title { font-size: 22px; font-weight: 800; color: #0f172a; margin: 0; }
          table { width: 100%; border-collapse: collapse; text-align: left; }
          th { background: #0f172a; color: #ffffff; font-size: 11px; text-transform: uppercase; font-weight: 700; padding: 10px 12px; }
          .footer { margin-top: 40px; text-align: center; font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 16px; }
        </style>
      </head>
      <body>
        <div class="header">
          <h1 class="title">DeployGuard Attendance History Log</h1>
          <div style="font-weight:700;">DogForce Security</div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Site</th>
              <th>Batch Status</th>
              <th>Present / Total</th>
              <th>Attendance %</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
        <div class="footer">
          Generated automatically via DogForce DeployGuard Mobile Suite • ${new Date().toLocaleString()}
        </div>
      </body>
    </html>
  `;

  try {
    const { uri } = await Print.printToFileAsync({ html });
    if (await Sharing.isAvailableAsync()) {
      await Sharing.shareAsync(uri, { UTI: '.pdf', mimeType: 'application/pdf' });
    }
  } catch (err) {
    console.error('PDF History Generation Error:', err);
    throw err;
  }
};
