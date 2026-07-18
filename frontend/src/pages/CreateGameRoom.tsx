import { useCreateGameRoom } from "../hooks/useCreateGameRoom";
import { TopBar } from "../components/createRoom/TopBar";
import { QuizSelectionList } from "../components/createRoom/QuizSelectionList";
import { Pagination } from "../components/pagination/Pagination";
import "../styles/createRoom/CreateGameRoom.css";

export default function CreateGameRoom() {
    const { state, actions } = useCreateGameRoom();
    
    return (
        <div className="mq-container">
            <header className="mq-header">
                <TopBar
                    onBack={actions.goHome}
                    onLogout={actions.logout}
                />
            </header>

            <main className="mq-main">
                <section className="mq-hero">
                    <h1 className="mq-logo">START<span>GAME</span></h1>
                    <p className="mq-lead">Choose a quiz and challenge your friends.</p>
                </section>

                <section className="mq-selection-wrapper">
                    <QuizSelectionList
                        quizzes={state.quizzes}
                        loading={state.loading}
                        error={state.error}
                        creatingRoomId={state.creatingRoomId}
                        onCreateRoom={actions.createRoom}
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