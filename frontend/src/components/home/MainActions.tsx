import "../../styles/home/MainActions.css";
import { Plus, Sparkles, Home, User } from "lucide-react"

export function MainActions({ authenticated, onCreateQuiz, onCreateRoom, onMyQuizzes, onGenerateAI }: any) {
    return (
        <div className="mq-actions-grid">
            <button className="mq-action-card create" onClick={onCreateQuiz}>
                <span className="mq-icon"><Plus size={32} strokeWidth={2.5} /></span>
                <span>Create Quiz</span>
            </button>

            <button className="mq-action-card ai-generate" onClick={onGenerateAI}>
                <span className="mq-icon"><Sparkles size={32} strokeWidth={2} /></span>
                <span>AI Generate</span>
            </button>
            
            <button className="mq-action-card room" onClick={onCreateRoom}>
                <span className="mq-icon"><Home size={32} strokeWidth={2} /></span>
                <span>Create Room</span>
            </button>

            {authenticated && (
                <button className="mq-action-card profile" onClick={onMyQuizzes}>
                    <span className="mq-icon"><User size={32} strokeWidth={2} /></span>
                    <span>My Quizzes</span>
                </button>
            )}
        </div>
    );
}