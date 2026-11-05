import { AssistantChat, type ChatTurn, type ImageChatContext } from './components/AssistantChat';

export function QuestionPage(props: {
  open: (id: string) => void;
  turns: ChatTurn[];
  setTurns: (turns: ChatTurn[]) => void;
  context: ImageChatContext | null;
  clearContext: () => void;
}) {
  return (
    <div className="assistant-page">
      <AssistantChat {...props} />
    </div>
  );
}
