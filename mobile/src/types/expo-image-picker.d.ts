declare module 'expo-image-picker' {
  export enum MediaTypeOptions {
    All = 'All',
    Videos = 'Videos',
    Images = 'Images',
  }

  export interface ImagePickerAsset {
    uri: string;
    width: number;
    height: number;
    type?: 'image' | 'video';
    base64?: string | null;
  }

  export interface ImagePickerResult {
    canceled: boolean;
    assets: ImagePickerAsset[];
  }

  export interface ImagePickerOptions {
    mediaTypes?: MediaTypeOptions;
    allowsEditing?: boolean;
    aspect?: [number, number];
    quality?: number;
    base64?: boolean;
  }

  export interface PermissionResponse {
    granted: boolean;
    status: string;
    expires: string | 'never';
    canAskAgain: boolean;
  }

  export function requestCameraPermissionsAsync(): Promise<PermissionResponse>;
  export function requestMediaLibraryPermissionsAsync(): Promise<PermissionResponse>;
  export function launchCameraAsync(options?: ImagePickerOptions): Promise<ImagePickerResult>;
  export function launchImageLibraryAsync(options?: ImagePickerOptions): Promise<ImagePickerResult>;
}
