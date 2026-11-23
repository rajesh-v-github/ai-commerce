function DraftResponseCard({ draft }) {
  const copyResponse = () => {
    navigator.clipboard.writeText(draft.ai_response);

    alert("Response copied successfully");
  };

  return (
    <div className="card mb-3">
      <div className="card-header">AI Draft Response</div>

      <div className="card-body">
        <textarea
          className="form-control"
          rows="8"
          readOnly
          value={draft.ai_response}
        />

        <button className="btn btn-success mt-3" onClick={copyResponse}>
          Copy Response
        </button>
      </div>
    </div>
  );
}

export default DraftResponseCard;
