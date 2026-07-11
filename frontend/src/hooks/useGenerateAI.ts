import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api/api";

interface AIQuestionField {
    question_text: string;
    options: string[];
    correct_answer_index: number;
}

interface AIResponse {
    title: string;
    description?: string;
    questions: AIQuestionField[];
}

interface EditableQuestion {
    text: string;
    options: string[];
    correctIndex: number;
}

export function useGenerateAI() {
    const navigate = useNavigate();

    const [topic, setTopic] = useState<string>("");
    const [numQuestions, setNumQuestions] = useState<number>(5);
    const [difficulty, setDifficulty] = useState<string>("medium");
    const [language, setLanguage] = useState<string>("English");

    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [previewQuiz, setPreviewQuiz] = useState<AIResponse | null>(null);

    const actions = {
        setTopic,
        setNumQuestions,
        setDifficulty,
        setLanguage,

        generate: async() => {
            if (!topic.trim()) {
                setError("Please provide a topic or description for your quiz.");
                return;
            }

            setLoading(true);
            setError(null);

            try {
                const data: AIResponse = await apiFetch("/v1/ai/generate", {
                    method: "POST",
                    body: JSON.stringify({
                        topic,
                        num_questions: numQuestions,
                        difficulty,
                        language
                    }),
                }, true);

                setPreviewQuiz(data);
            } catch (err: any) {
                setError(err.message || "Failed to generate quiz. Please try again.");
            } finally {
                setLoading(false);
            }
        },

        updateTitle: (value: string) => {
            if (!previewQuiz) return;
            setPreviewQuiz({ ...previewQuiz, title: value });
        },

        updateDescription: (value: string) => {
            if (!previewQuiz) return;
            setPreviewQuiz({ ...previewQuiz, description: value });
        },

        updateQuestionText: (index: number, value: string) => {
            if (!previewQuiz) return;
            const updatedQuestions = [...previewQuiz.questions];
            updatedQuestions[index].question_text = value;
            setPreviewQuiz({ ...previewQuiz, questions: updatedQuestions });
        },

        updateOption: (qIndex: number, optIndex: number, value: string) => {
            if (!previewQuiz) return;
            const updatedQuestions = [...previewQuiz.questions];
            updatedQuestions[qIndex].options[optIndex] = value;
            setPreviewQuiz({ ...previewQuiz, questions: updatedQuestions });
        },

        setCorrectOption: (qIndex: number, idx: number) => {
            if (!previewQuiz) return;
            const updatedQuestions = [...previewQuiz.questions];
            updatedQuestions[qIndex].correct_answer_index = idx;
            setPreviewQuiz({ ...previewQuiz, questions: updatedQuestions });
        },

        cancelPreview: () => {
            setPreviewQuiz(null);
        },

        goHome: () => navigate("/"),

        saveQuiz: async () => {
            if (!previewQuiz || !previewQuiz.title.trim()) {
                alert("Plase make sure the quiz has a title.");
                return;
            }

            for (const q of previewQuiz.questions) {
                if (!q.question_text.trim() || q.options.some(opt => !opt.trim())) {
                    alert("All questions and options must be filled before saving.");
                    return;
                }
            }

            const formattedQuestions = previewQuiz.questions.map((q, i) => ({
                id: `q${i + 1}`,
                question_text: q.question_text,
                options: q.options,
                correct_option: q.options[q.correct_answer_index]
            }));

            try {
                await apiFetch("/quizzes/", {
                    method: "POST",
                    body: JSON.stringify({
                        title: previewQuiz.title,
                        questions: formattedQuestions
                    }),
                }, true);

                navigate("/");
            } catch (err: any) {
                alert("Error saving the generated quiz: " + err.message);
            }
        }
    };

    const isPreviewValid = !!previewQuiz && previewQuiz.title.trim().length > 0;

    return {
        state: {
            topic,
            numQuestions,
            difficulty,
            language,
            loading,
            error,
            previewQuiz,
            isPreviewValid
        },
        actions
    };
}