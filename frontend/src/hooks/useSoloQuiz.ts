import { useParams, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { QuizWithQuestions } from "../types/quiz";
import { quizService } from "../services/quizService";

export function useSoloQuiz() {
    const { id } = useParams<{ id: string}>();
    const navigate = useNavigate();

    const [quiz, setQuiz] = useState<QuizWithQuestions | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [currentIndex, setCurrentIndex] = useState(0);
    const [selectedOption, setSelectedOption] = useState<string | null>(null);
    const [showResult, setShowResult] = useState(false);
    const [isCorrect, setIsCorrect] = useState<boolean | null>(null);
    const [score, setScore] = useState(0);

    useEffect(() => {
        const fetchQuiz = async () => {
            if (!id) return;

            setLoading(true);
            setError(null);

            try {
                const data = await quizService.getQuiz(id);
                setQuiz(data);
            } catch (err: any) {
                setError(err.message || "Failed to load quiz");
            } finally {
                setLoading(false);
            }
        };

        fetchQuiz();
    }, [id]);

    const currentQuestion = quiz?.questions[currentIndex] || null;

    const actions = {
        goHome: () => navigate("/"),

        selectOption: async (option: string) => {
            if (!quiz || !currentQuestion || showResult) return;

            setSelectedOption(option);

            try {
                const result = await quizService.checkAnswer(quiz.quizId, {
                    question_id: currentQuestion.id,
                    answer: option
                });

                setIsCorrect(result.correct);
                setShowResult(true);

                if (result.correct) {
                    setScore((prev) => prev + 1);
                }
            } catch {
                alert("Error checking anwer");
            }
        },

        next: () => {
            if (!quiz) return;

            setSelectedOption(null);
            setShowResult(false);
            setIsCorrect(null);

            if (currentIndex < quiz.questions.length - 1) {
                setCurrentIndex((prev) => prev + 1);
            } else {
                alert(
                    `Quiz finished! Score: ${score}/${quiz.questions.length}`
                );
                navigate("/");
            }
        }
    };

    return {
        state: {
            quiz,
            loading,
            error,
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