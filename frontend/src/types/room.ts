/* Domain models */

export type Role = "host" | "player";

export type RoomViewState = 
    | "ENTER_NAME"
    | "WAITING"
    | "QUESTION"
    | "LEADERBOARD"
    | "FINISHED";

export interface Question {
    text: string;
    options: string[];
    duration?: number;
}

export interface LeaderboardEntry {
    name: string;
    score: number;
}

/* API Responses */

export interface CreateRoomResponse {
    room_id: number;
}