import { apiClient } from "../api/apiClient";
import { CreateRoomResponse } from "../types/room";

export const gameService = {
    createRoom(quizId: string): Promise<CreateRoomResponse> {
        return apiClient<CreateRoomResponse>(`/game/${quizId}/create_room`, {
            method: "POST",
            requireAuth: true
        })
    }
}