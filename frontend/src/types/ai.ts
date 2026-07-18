/* API Requests */

export interface GenerateQuizRequest {
    topic: string;
    num_questions: number;
    difficulty: string;
    language: string;
}

/* API Responses */

export interface GenerateQuizResponse {
    title: string;
    description: string;
    questions: GenerateQuizQuestionResponse[];
}

export interface GenerateQuizQuestionResponse {
    question_text: string;
    options: string[];
    correct_answer_index: number;
}