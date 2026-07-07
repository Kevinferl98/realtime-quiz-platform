import "../../styles/myQuizzes/MyQuizList.css"
import { FileText, Trash2 } from "lucide-react";

interface Quiz {
    quizId: string;
    title: string;
}

interface Props {
    quizzes: Quiz[];
    loading: boolean;
    error: string | null;
    onPlay: (quizId: string) => void;
    onDelete: (quizId: string) => void;
}

export function MyQuizList({
    quizzes,
    loading,
    error,
    onPlay,
    onDelete
}: Props) {
    return (
        <div className="mq-list-container">
            {loading && (
                <div className="mq-loader-wrapper">
                    <div className="mq-loader"></div>
                    <p>Loading your quizzes...</p>
                </div>
            )}
            
            {error && <div className="mq-error-banner">{error}</div>}

            {!loading && !error && quizzes.length === 0 && (
                <div className="mq-empty-state">
                    <span className="mq-empty-icon"><FileText size={48} strokeWidth={1.5} /></span>
                    <p>You haven't created any quizzes yet.</p>
                </div>
            )}

            <div className="mq-quiz-grid">
                {quizzes.map((quiz) => (
                    <div key={quiz.quizId} className="mq-quiz-card-manage">
                        <div className="mq-quiz-card-content">
                            <h3>{quiz.title}</h3>
                            <p className="mq-quiz-stats">Public Quiz</p>
                        </div>

                        <div className="mq-card-actions">
                            <button
                                className="mq-btn-action play"
                                onClick={() => onPlay(quiz.quizId)}
                            >
                                Play
                            </button>

                            <button
                                className="mq-btn-action-danger"
                                onClick={() => onDelete(quiz.quizId)}
                                title="Delete Quiz"
                            >
                                <span className="mq-icon-trash"><Trash2 size={18} strokeWidth={2} /></span>
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}