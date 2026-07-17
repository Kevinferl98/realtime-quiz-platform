/* Domain models */

export interface Quiz {
    quizId: string;
    title: string;
}

export interface QuizWithQuestions {
  quizId: string;
  title: string;
  questions: QuizDetailQuestions[];
}

export interface QuizDetailQuestions {
  id: string;
  question_text: string;
  options: string[];
}

/* Form models */

export interface QuizFormQuestion {
  text: string;
  options: string[];
  correctIndex: number;
}

/* API Requests */

export interface CreateQuizQuestionRequest {
  id: string;
  question_text: string;
  options: string[];
  correct_option: string;
}

export interface CreateQuizRequest {
  title: string;
  questions: CreateQuizQuestionRequest[];
}

export interface CheckAnswerRequest {
  question_id: string;
  answer: string;
}

/* API Responses */

export interface QuizzesResponse {
  quizzes: Quiz[];
}

export interface PublicQuizzesResponse extends QuizzesResponse {
  total: number;
  page: number;
  pages: number;
}

export interface CreateQuizResponse {
  quizId: string;
}

export interface CheckAnswerReseponse {
  correct: boolean;
}