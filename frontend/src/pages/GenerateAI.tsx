import { useGenerateAI } from "../hooks/useGenerateAI";
import { AIConfigForm } from "../components/generateAI/AIConfigForm";
import { ActionsButtons } from "../components/createQuiz/ActionsButtons";
import { Loader2, Wand2 } from "lucide-react";
import "../styles/createQuiz/CreateQuiz.css";
import "../styles/createQuiz/QuizForm.css";
import "../styles/generateAI/GenerateAI.css";

export default function GenerateAI() {
  const { state, actions } = useGenerateAI();

  return (
    <div className="mq-container">
      <header className="mq-hero">
        <h1 className="mq-logo ai-gradient-text">AI<span>GENERATOR</span></h1>
        <p className="mq-lead">Let artificial intelligence design a customized set of questions in seconds.</p>
      </header>

      <main className="mq-create-wrapper">
        {state.loading && (
          <div className="mq-ai-loader-container">
            <div className="mq-spinner-wrapper">
              <Loader2 className="mq-animate-spin" size={48} />
              <Wand2 className="mq-pulse-icon" size={24} />
            </div>
            <h3>Generating your quiz...</h3>
            <p>The AI is crafting balanced questions and verified options. This may take a few seconds.</p>
          </div>
        )}

        {state.error && (
          <div className="mq-error-banner-ai">
            <p>{state.error}</p>
          </div>
        )}

        {!state.loading && !state.previewQuiz && (
          <AIConfigForm
            topic={state.topic}
            numQuestions={state.numQuestions}
            difficulty={state.difficulty}
            language={state.language}
            onTopicChange={actions.setTopic}
            onNumQuestionsChange={actions.setNumQuestions}
            onDifficultyChange={actions.setDifficulty}
            onLanguageChange={actions.setLanguage}
            onSubmit={actions.generate}
            onCancel={actions.goHome}
          />
        )}

        {!state.loading && state.previewQuiz && (
          <div className="mq-form-container">
            <div className="mq-ai-preview-badge">
              <span>Preview Mode: Review or edit before saving</span>
            </div>

            <section className="mq-form-section">
              <label className="mq-label">Quiz Title</label>
              <input
                className="mq-input-title"
                type="text"
                value={state.previewQuiz.title}
                onChange={(e) => actions.updateTitle(e.target.value)}
              />
            </section>

            <div className="mq-section-header">
              <h2 className="mq-section-title">Generated Questions</h2>
            </div>

            <div className="mq-questions-list">
              {state.previewQuiz.questions.map((q, qIdx) => (
                <div key={qIdx} className="mq-question-card">
                  <div className="mq-question-header">
                    <span className="mq-question-number">#{qIdx + 1}</span>
                    <input
                      className="mq-input-question"
                      type="text"
                      value={q.question_text}
                      onChange={(e) => actions.updateQuestionText(qIdx, e.target.value)}
                    />
                  </div>

                  <div className="mq-options-grid">
                    {q.options.map((opt, idx) => (
                      <div key={idx} className={`mq-option-item ${q.correct_answer_index === idx ? 'is-correct' : ''}`}>
                        <label className="mq-radio-container">
                          <input
                            type="radio"
                            name={`correct-${qIdx}`}
                            checked={q.correct_answer_index === idx}
                            onChange={() => actions.setCorrectOption(qIdx, idx)}
                          />
                          <span className="mq-checkmark"></span>
                        </label>
                        <input
                          className="mq-input-option"
                          type="text"
                          value={opt}
                          onChange={(e) => actions.updateOption(qIdx, idx, e.target.value)}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <ActionsButtons
              onSubmit={actions.saveQuiz}
              onCancel={actions.cancelPreview}
              disabled={!state.isPreviewValid}
            />
          </div>
        )}
      </main>
    </div>
  );
}