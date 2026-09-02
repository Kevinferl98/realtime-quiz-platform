import { apiClient } from "../api/apiClient";
import { CreateRoomResponse, WSTicketResponse } from "../types/room";

export const gameService = {
    createRoom(quizId: string): Promise<CreateRoomResponse> {
        return apiClient<CreateRoomResponse>(`/game/${quizId}/create_room`, {
            method: "POST",
            requireAuth: true
        })
    },

    getWSTicket(roomId: string): Promise<WSTicketResponse> {
        return apiClient<WSTicketResponse>(`/game/rooms/${roomId}/ws-ticket`, {
            method: "POST",
            requireAuth: true
        })
    } 
}