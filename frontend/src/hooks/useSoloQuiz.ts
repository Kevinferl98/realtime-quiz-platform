import { useParams, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useGetQuiz, useCheckAnswer } from "./queries/useQuizQueries";

export function useSoloQuiz() {
    const { id } = useParams();
    const navigate = useNavigate();

    const { data, isLoading, isError, error } = useGetQuiz(id);

    const checkAnswerMutation = useCheckAnswer();

    const [currentIndex, setCurrentIndex] = useState(0);
    const [selectedOption, setSelectedOption] = useState<string | null>(null);
    const [showResult, setShowResult] = useState(false);
    const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
    const [score, setScore] = useState(0);

    const currentQuestion = data?.questions[currentIndex] || null;

    const actions = {
        goHome: () => navigate("/"),

        selectOption: async (option: string) => {
            if (!data || !currentQuestion || !id || showResult || checkAnswerMutation.isPending) return;

            setSelectedOption(option);

            checkAnswerMutation.mutate(
                {
                    quizId: id,
                    request: {
                        question_id: currentQuestion.id,
                        answer: option
                    }
                },
                {
                    onSuccess: (result) => {
                        setIsCorrect(result.correct);
                        setShowResult(true);

                        if (result.correct) {
                            setScore((prev) => prev + 1)
                        }
                    }
                }
            );
        },

        next: () => {
            if (!data) return;

            setSelectedOption(null);
            setShowResult(false);
            setIsCorrect(null);

            if (currentIndex < data.questions.length - 1) {
                setCurrentIndex((prev) => prev + 1);
            } else {
                alert(
                    `Quiz finished! Score: ${score}/${data.questions.length}`
                );
                navigate("/");
            }
        }
    };

    return {
        state: {
            quiz: data || null,
            loading: isLoading,
            error: isError ? (error as Error).message || "Failed to load quiz" : null,
            currentIndex,
            currentQuestion,
            selectedOption,
            showResult,
            isCorrect,
            score
        },
        actions
    };
}