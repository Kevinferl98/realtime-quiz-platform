import { useHomePage } from "../hooks/useHomePage";
import { AuthBar } from "../components/home/AuthBar";
import { JoinRoom } from "../components/home/JoinRoom";
import { MainActions } from "../components/home/MainActions";
import { QuizList } from "../components/home/QuizList";
import { Pagination } from "../components/home/Pagination";
import "../styles/home/HomePage.css";

export default function HomePage() {
  const { state, actions } = useHomePage();

  return (
    <div className="mq-container">
      <header className="mq-header">
        <AuthBar
          authenticated={state.authenticated}
          username={state.username}
          onLogin={actions.login}
          onLogout={actions.logout}
        />
      </header>

      <main className="mq-main">
        <section className="mq-hero">
          <h1 className="mq-logo">QUIZ<span>PLATFORM</span></h1>
          <p className="mq-lead">Create, challenge, and win in real time.</p>
        </section>

        <section className="mq-section-join">
          <JoinRoom
            roomCode={state.roomCode}
            onChange={actions.setRoomCode}
            onJoin={actions.joinRoom}
          />
        </section>

        <section className="mq-section-actions">
          <MainActions
            authenticated={state.authenticated}
            onCreateQuiz={actions.createQuiz}
            onCreateRoom={actions.createRoom}
            onMyQuizzes={actions.goToMyQuizzes}
            onGenerateAI={actions.generateAI}
          />
        </section>

        <section className="mq-section-list">
          <QuizList
            quizzes={state.quizzes}
            loading={state.loading}
            error={state.error}
            onPlay={actions.playSolo}
          />
        </section>

        <footer className="mq-footer">
          <Pagination
            page={state.page}
            pages={state.pages}
            onChange={actions.setPage}
          />
        </footer>
      </main>
    </div>
  );
}