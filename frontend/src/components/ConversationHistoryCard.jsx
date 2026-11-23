function ConversationHistoryCard({ messages }) {
  if (!messages) {
    return null;
  }

  return (
    <div className="card mb-3">
      <div className="card-header">Conversation History</div>

      <div className="card-body">
        {messages.map((msg) => (
          <div key={msg.id} className="border-bottom pb-2 mb-2">
            <strong className="ticket-summary-field-label">
              User {msg.user_id}
            </strong>

            <br />

            {msg.message}
          </div>
        ))}
      </div>
    </div>
  );
}

export default ConversationHistoryCard;
