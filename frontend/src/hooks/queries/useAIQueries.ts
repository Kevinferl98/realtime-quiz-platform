import { useMutation } from "@tanstack/react-query";
import { aiService } from "../../services/aiService";
import { GenerateQuizRequest } from "../../types/ai";

export function useGenerateAIQuiz() {
    return useMutation({
        mutationFn: (request: GenerateQuizRequest) => aiService.generateQuiz(request),
        onError: (error: any) => {
            alert(error.message || "Failed to generate quiz. Please try again.");
        }
    });
}