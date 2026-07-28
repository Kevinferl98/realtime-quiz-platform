import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { quizService } from "../../services/quizService";
import { queryKeys } from "../../queries/queryKeys";
import { CheckAnswerRequest, CreateQuizRequest } from "../../types/quiz";

export function usePublicQuizzes(page: number, limit: number) {
    return useQuery({
        queryKey: queryKeys.quizzes.public(page, limit),
        queryFn: () => quizService.getPublicQuizzes(page, limit),
        placeholderData: keepPreviousData
    });
}

export function useMyQuizzeList(enabled = true) {
    return useQuery({
        queryKey: queryKeys.quizzes.mine(),
        queryFn: () => quizService.getMyQuizzes(),
        enabled
    });
}

export function useCreateQuizMutation() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (newQuiz: CreateQuizRequest) => quizService.createQuiz(newQuiz),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.quizzes.all });
        },
        onError: (error: any) => {
            alert("Error creating quiz: " + (error.message || "Unknown error"));
        }
    });
}

export function useDeleteQuiz() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (quizId: string) => quizService.deleteQuiz(quizId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.quizzes.all });
        }
    });
}

export function useGetQuiz(quizId?: string) {
    return useQuery({
        queryKey: queryKeys.quizzes.detail(quizId || ""),
        queryFn: () => quizService.getQuiz(quizId!),
        enabled: Boolean(quizId)
    });
}

export function useCheckAnswer() {
    return useMutation({
        mutationFn: ({ quizId, request }: { quizId: string, request: CheckAnswerRequest }) => quizService.checkAnswer(quizId, request),
        onError: (error: any) => {
            alert(error.message || "Error checking answer");
        }
    });
}