import { apiClient } from "../api/apiClient";
import { 
  QuizWithQuestions, 
  QuizzesResponse, 
  PublicQuizzesResponse, 
  CreateQuizRequest, 
  CreateQuizResponse, 
  CheckAnswerRequest,
  CheckAnswerReseponse 
} from "../types/quiz";

export const quizService = {
  getPublicQuizzes(page: number, limit: number): Promise<PublicQuizzesResponse> {
    return apiClient<PublicQuizzesResponse>(
      `/quizzes/public?page=${page}&limit=${limit}`
    );
  },

  getQuiz(quizId: string): Promise<QuizWithQuestions> {
    return apiClient<QuizWithQuestions>(`/quizzes/${quizId}`);
  },

  getMyQuizzes() {
    return apiClient<QuizzesResponse>("/quizzes/mine", {
      requireAuth: true
    });
  },

  deleteQuiz(quizId: string) {
    return apiClient<void>(`/quizzes/${quizId}`, {
      method: "DELETE",
      requireAuth: true
    })
  },

  createQuiz(request: CreateQuizRequest) {
    return apiClient<CreateQuizResponse>("/quizzes/", {
      method: "POST",
      requireAuth: true,
      body: JSON.stringify(request)
    });
  },

  checkAnswer(quizId: string, request: CheckAnswerRequest) {
    return apiClient<CheckAnswerReseponse>(`/quizzes/${quizId}/answer`, {
      method: "POST",
      body: JSON.stringify(request)
    })
  }
};