import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { quizService } from "../services/quizService";
import { QuizFormQuestion } from "../types/quiz";

export function useCreateQuiz() {
    const navigate = useNavigate();

    const [title, setTitle] = useState<string>("");
    const [questions, setQuestions] = useState<QuizFormQuestion[]>([]);

    const actions = {
        setTitle,

        addQuestion: () => {
            setQuestions((prev) => [
                ...prev,
                { text: "", options: ["", "", "", ""], correctIndex: 0},
            ]);
        },

        updateQuestionText: (index: number, value: string) => {
            setQuestions((prev) => {
                const updated = [...prev];
                updated[index].text = value;
                return updated;
            });
        },

        updateOption: (qIndex: number, optIndex: number, value: string) => {
            setQuestions((prev) => {
                const updated = [...prev];
                updated[qIndex].options[optIndex] = value;
                return updated;
            });
        },

        setCorrectOption: (qIndex: number, idx: number) => {
            setQuestions((prev) => {
                const updated = [...prev];
                updated[qIndex].correctIndex = idx;
                return updated;
            });
        },

        goHome: () => navigate("/"),

        submit: async () => {
            if (!isValidQuiz(title, questions)) {
                alert("Plaese fill in the quiz title and all question fields.");
                return;
            }

            const formattedQuestions = questions.map((q, i) => ({
                id: `q${i + 1}`,
                question_text: q.text,
                options: q.options,
                correct_option: q.options[q.correctIndex]
            }));

            try {
                const data = await quizService.createQuiz({
                    title,
                    questions: formattedQuestions
                })

                console.log("Quiz created with ID:", data.quizId);
                navigate("/");
            } catch (error: any) {
                alert("Error creating quiz: " + error.message);
            }
        }
    };

    const isValid = isValidQuiz(title, questions);

    return {
        state: {
            title,
            questions,
            isValid
        },
        actions
    };
}

function isValidQuiz(title: string, questions: QuizFormQuestion[]): boolean {
    if (!title.trim()) return false;
    if (questions.length === 0) return false;

    for (const q of questions) {
        if (!q.text.trim()) return false;
        if (q.options.some((opt) => !opt.trim())) return false;
    }

    return true;
}