import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { quizService } from "../../services/quizService";
import { queryKeys } from "../../queries/queryKeys";
import { CreateQuizRequest } from "../../types/quiz";

export function usePublicQuizzes(page: number, limit: number) {
    return useQuery({
        queryKey: queryKeys.quizzes.public(page, limit),
        queryFn: () => quizService.getPublicQuizzes(page, limit),
        placeholderData: keepPreviousData
    });
}

export function useMyQuizzes(enabled = true) {
    return useQuery({
        queryKey: queryKeys.quizzes.mine(),
        queryFn: () => quizService.getMyQuizzes(),
        enabled
    });
}

export function useCreateQuiz() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (newQuiz: CreateQuizRequest) => quizService.createQuiz(newQuiz),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.quizzes.mine() });
        }
    });
}

export function useDeleteQuiz() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (quizId: string) => quizService.deleteQuiz(quizId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.quizzes.mine() });
        }
    });
}