import { apiClient } from "../api/apiClient";
import { GenerateQuizRequest, GenerateQuizResponse } from "../types/ai";

export const aiService = {
    generateQuiz(request: GenerateQuizRequest) {
        return apiClient<GenerateQuizResponse>("/v1/ai/generate", {
            method: "POST",
            requireAuth: true,
            body: JSON.stringify(request)
        })
    }
}