declare module 'expo-location' {
  export enum Accuracy {
    Lowest = 1,
    Low = 2,
    Balanced = 3,
    High = 4,
    Highest = 5,
    BestForNavigation = 6,
  }

  export interface LocationPermissionResponse {
    status: string;
    granted: boolean;
    expires: string | 'never';
    canAskAgain: boolean;
  }

  export interface LocationObjectCoords {
    latitude: number;
    longitude: number;
    altitude: number | null;
    accuracy: number | null;
    altitudeAccuracy: number | null;
    heading: number | null;
    speed: number | null;
  }

  export interface LocationObject {
    coords: LocationObjectCoords;
    timestamp: number;
  }

  export interface PositionOptions {
    accuracy?: Accuracy;
    timeInterval?: number;
    distanceInterval?: number;
  }

  export function requestForegroundPermissionsAsync(): Promise<LocationPermissionResponse>;
  export function getCurrentPositionAsync(options?: PositionOptions): Promise<LocationObject>;
}
