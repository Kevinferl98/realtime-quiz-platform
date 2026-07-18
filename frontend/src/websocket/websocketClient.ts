import { ClientMessage, ServerMessage } from "../types/roomMessages";

type MessageHandler = (message: ServerMessage) => void;
type VoidHandler = () => void;

export class WebSocketClient {
    private socket: WebSocket | null = null;

    private messageHandler?: MessageHandler;
    private openHandler?: VoidHandler;
    private closeHandler?: VoidHandler;

    constructor(private readonly url: string) {}

    connect(): void {
        if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
            return;
        }

        this.socket = new WebSocket(this.url);

        this.socket.onopen = () => {
            this.openHandler?.();
        };

        this.socket.onmessage = (event: MessageEvent<string>) => {
            const message = JSON.parse(event.data) as ServerMessage;
            this.messageHandler?.(message);
        };

        this.socket.onclose = () => {
            this.closeHandler?.();
        };
    }

    disconnect(): void {
        this.socket?.close();
        this.socket = null;
    }

    send(message: ClientMessage): void {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            return;
        }

        this.socket.send(JSON.stringify(message));
    }

    onMessage(handler: MessageHandler): void {
        this.messageHandler = handler;
    }

    onOpen(handler: VoidHandler): void {
        this.openHandler = handler;
    }

    onClose(handler: VoidHandler): void {
        this.closeHandler = handler;
    }

    get connected(): boolean {
        return this.socket?.readyState === WebSocket.OPEN;
    }
}
