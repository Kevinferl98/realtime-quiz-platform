import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { GenerateQuizResponse } from "../types/ai";
import { useGenerateAIQuiz } from "./queries/useAIQueries";
import { useCreateQuizMutation } from "./queries/useQuizQueries";

export function useGenerateAI() {
    const navigate = useNavigate();

    const [topic, setTopic] = useState<string>("");
    const [numQuestions, setNumQuestions] = useState<number>(5);
    const [difficulty, setDifficulty] = useState<string>("medium");
    const [language, setLanguage] = useState<string>("English");

    const [previewQuiz, setPreviewQuiz] = useState<GenerateQuizResponse | null>(null);
    const [validationError, setValidationError] = useState<string | null>(null);

    const generateMutation = useGenerateAIQuiz();
    const createQuizMutation = useCreateQuizMutation();

    const actions = {
        setTopic,
        setNumQuestions,
        setDifficulty,
        setLanguage,

        generate: async() => {
            if (!topic.trim()) {
                setValidationError("Please provide a topic or description for your quiz.");
                return;
            }

            setValidationError(null);

            generateMutation.mutate(
                {
                    topic,
                    num_questions: numQuestions,
                    difficulty,
                    language
                },
                {
                    onSuccess: (data) => {
                        setPreviewQuiz(data);
                    }
                }
            );
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
            generateMutation.reset();
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

            createQuizMutation.mutate(
                {
                    title: previewQuiz.title,
                    questions: formattedQuestions
                },
                {
                    onSuccess: () => {
                        navigate("/");
                    }
                }
            );
        }
    };

    const isPreviewValid = !!previewQuiz && previewQuiz.title.trim().length > 0;
    const loading = generateMutation.isPending || createQuizMutation.isPending;
    const error = validationError || (generateMutation.isError ? (generateMutation.error as Error).message : null);

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