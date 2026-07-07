import { Sparkles } from "lucide-react";
import "../../styles/generateAI/AIConfigForm.css";

interface Props {
    topic: string;
    numQuestions: number;
    difficulty: string;
    onTopicChange: (val: string) => void;
    onNumQuestionsChange: (val: number) => void;
    onDifficultyChange: (val: string) => void;
    onSubmit: () => void;
    onCancel: () => void;
}

export function AIConfigForm({
    topic,
    numQuestions,
    difficulty,
    onTopicChange,
    onNumQuestionsChange,
    onDifficultyChange,
    onSubmit,
    onCancel
}: Props) {
    return (
        <div className="mq-form-container">
            <section className="mq-form-section">
                <label className="mq-label">Topic or Context</label>
                <textarea
                    className="mq-textarea-topic"
                    placeholder="E.g., History of Space Exploration..."
                    value={topic}
                    onChange={(e) => onTopicChange(e.target.value)}
                    rows={3}
                />
            </section>

            <div className="mq-config-row">
                <section className="mq-form-section flex-1">
                    <label className="mq-label">Number of questions</label>
                    <input
                        className="mq-input-select"
                        type="number"
                        min={1}
                        max={15}
                        value={numQuestions}
                        onChange={(e) => onNumQuestionsChange(parseInt(e.target.value, 10) || 5)}
                    />
                </section>

                <section className="mq-form-section flex-1">
                    <label className="mq-label">Difficulty</label>
                    <select
                        className="mq-input-select"
                        value={difficulty}
                        onChange={(e) => onDifficultyChange(e.target.value)}
                    >
                        <option value="easy">Easy</option>
                        <option value="medium">Medium</option>
                        <option value="hard">Hard</option>
                    </select>
                </section>
            </div>

            <div className="mq-actions-footer no-border">
                <button className="mq-btn-secondary-lg" onClick={onCancel}>Cancel</button>
                <button className="mq-btn-primary-lg ai-magic-btn" onClick={onSubmit} disabled={!topic.trim()}>
                    <Sparkles size={18} strokeWidth={2.5} />
                    Generate with AI
                </button>
            </div>
        </div>
    );
}