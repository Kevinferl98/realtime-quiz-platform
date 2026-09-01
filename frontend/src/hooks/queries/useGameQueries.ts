import { useMutation } from "@tanstack/react-query";
import { gameService } from "../../services/gameService";

export function useCreateRoom() {
    return useMutation({
        mutationFn: (quizId: string) => gameService.createRoom(quizId),
        onError: (error: any) => {
            alert(error.message || "Error creating room");
        },
    });
}

export function useGetWSTicketMutation() {
    return useMutation({
        mutationFn: (roomId: string) => gameService.getWSTicket(roomId)
    });
}