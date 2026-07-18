import { LeaderboardEntry, Question, Role } from "./room";

/* Client -> Server */

export interface JoinMessage {
    type: "join";
    name: string;
}

export interface StartMessage {
    type: "start";
}

export interface AnswerMessage {
    type: "answer";
    answer: string;
}

export type ClientMessage = 
    | JoinMessage
    | StartMessage
    | AnswerMessage;

/* Server -> Client */

export interface RoleMessage {
    type: "role";
    role: Role;
    player_id: string;
}

export interface PlayerJoinedMessage {
    type: "player_joined";
    players: string[];
}

export interface PlayerLeftMessage {
    type: "player_left";
    players: string[];
}

export interface QuestionMessage {
    type: "question";
    question: Question;
}

export interface TimerMessage {
    type: "timer";
    seconds: number;
}

export interface AnswerResultMessage {
    type: "answer_result";
    correct_answer: string;
}

export interface LeaderboardMessage {
    type: "leaderboard";
    leaderboard: LeaderboardEntry[];
    final: boolean;
}

export interface ErrorMessage {
    type: "error";
    code: string;
    message: string;
}

export type ServerMessage =
    | RoleMessage
    | PlayerJoinedMessage
    | PlayerLeftMessage
    | QuestionMessage
    | TimerMessage
    | AnswerResultMessage
    | LeaderboardMessage
    | ErrorMessage;