import { CONFIG } from "../config";
import { WebSocketClient } from "./websocketClient";
import { ServerMessage } from "../types/roomMessages";
import { Question, LeaderboardEntry, Role } from "../types/room";

interface RoomSocketHandlers {
    onRole?: (role: Role, playerId: string) => void;
    onPlayersChanged?: (players: string[]) => void;
    onQuestion?: (question: Question) => void;
    onTimer?: (seconds: number) => void;
    onAnswerResult?: (correctAnswer: string) => void;
    onLeaderboard?: (leaderboard: LeaderboardEntry[], final: boolean) => void;
    onError?: (code: string, message: string) => void;
}

export class RoomSocket {
    private client: WebSocketClient;

    constructor(private readonly roomId: string, private readonly token?: string) {
        const tokenQuery = token ? `?token=${token}` : "";
        const url = `${CONFIG.WS_BASE}/rooms/${roomId}${tokenQuery}`;
        this.client = new WebSocketClient(url);
    }

    connect(handlers: RoomSocketHandlers): void {
        this.client.onMessage(
            (message) => {
                this.handleMessage(message, handlers);
            }
        );

        this.client.connect();
    }

    disconnect(): void {
        this.client.disconnect();
    }

    onOpen(callback: () => void): void {
        this.client.onOpen(callback);
    }

    onClose(callback: () => void): void {
        this.client.onClose(callback);
    }

    join(name: string): void {
        this.client.send({
            type: "join",
            name
        });
    }

    start(): void {
        this.client.send({
            type: "start"
        });
    }

    answer(answer: string) {
        this.client.send({
            type: "answer",
            answer
        });
    }

    private handleMessage(message: ServerMessage, handlers: RoomSocketHandlers): void {
        switch (message.type) {
            case "role":
                handlers.onRole?.(message.role, message.player_id);
                break;
            case "player_joined":
            case "player_left":
                handlers.onPlayersChanged?.(message.players);
                break;
            case "question":
                handlers.onQuestion?.(message.question);
                break;
            case "timer":
                handlers.onTimer?.(message.seconds);
                break;
            case "answer_result":
                handlers.onAnswerResult?.(message.correct_answer);
                break;
            case "leaderboard":
                handlers.onLeaderboard?.(message.leaderboard, message.final);
                break;
            case "error":
                handlers.onError?.(message.code, message.message);
                break;
        }
    }
}