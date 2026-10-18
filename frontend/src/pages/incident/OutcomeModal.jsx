export default function OutcomeModal({
  type, feedback, submitting, onFeedbackChange, onSubmit, onClose,
}) {
  return (
    <div
      className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Remediation outcome"
    >
      <div className="card max-w-md w-full border border-dt-border bg-dt-dark p-6 rounded-2xl shadow-2xl animate-fade-in text-white">

        {type === 'success' && (
          <div className="text-center space-y-4">
            <div className="w-12 h-12 bg-green-500/20 text-green-400 rounded-full flex items-center justify-center mx-auto text-2xl font-bold" aria-hidden="true">
              ✓
            </div>
            <h3 className="text-lg font-bold">Remediation Logged</h3>
            <p className="text-dt-text/70 text-sm">Thanks!</p>
            <button onClick={onClose} className="btn-primary w-full py-2 font-semibold">
              OK
            </button>
          </div>
        )}

        {type === 'failed' && (
          <div className="text-center space-y-4">
            <div className="w-12 h-12 bg-red-500/20 text-red-400 rounded-full flex items-center justify-center mx-auto text-2xl font-bold" aria-hidden="true">
              ✗
            </div>
            <h3 className="text-lg font-bold">Remediation Logged</h3>
            <p className="text-dt-text/70 text-sm">
              Ok, we will feed this to train our model.
            </p>
            <div className="flex flex-col gap-2 pt-2">
              <a
                href="https://support.dynatrace.com"
                target="_blank"
                rel="noreferrer"
                className="btn-primary w-full py-2 font-semibold block text-center"
              >
                Raise Support Ticket
              </a>
              <button
                onClick={onClose}
                className="btn-ghost w-full py-2 font-semibold text-dt-text/60 hover:text-white"
              >
                Close
              </button>
            </div>
          </div>
        )}

        {type === 'partial' && (
          <div className="space-y-4">
            <h3 className="text-lg font-bold flex items-center gap-2">
              <span className="text-yellow-400" aria-hidden="true">⚠️</span> Describe Partial Success
            </h3>
            <p className="text-dt-text/70 text-sm">
              We have logged the partial recovery. To help train our remediation advisor, please describe what worked:
            </p>
            <textarea
              className="w-full bg-dt-dark border border-dt-border rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-dt-blue"
              rows="4"
              aria-label="Describe what worked"
              placeholder="e.g. The service restarted and database connectivity was restored, but memory footprint remains elevated..."
              value={feedback}
              onChange={(e) => onFeedbackChange(e.target.value)}
            />
            <div className="flex gap-3 pt-2">
              <button
                onClick={onClose}
                className="btn-ghost flex-1 py-2 font-semibold text-dt-text/60 hover:text-white"
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                onClick={onSubmit}
                className="btn-primary flex-1 py-2 font-semibold"
                disabled={submitting || !feedback.trim()}
              >
                {submitting ? 'Saving...' : 'Submit'}
              </button>
            </div>
          </div>
        )}

        {type === 'partial-confirmed' && (
          <div className="text-center space-y-4">
            <div className="w-12 h-12 bg-yellow-500/20 text-yellow-400 rounded-full flex items-center justify-center mx-auto text-2xl font-bold" aria-hidden="true">
              ✓
            </div>
            <h3 className="text-lg font-bold">Feedback Saved</h3>
            <p className="text-dt-text/70 text-sm">
              Thanks for your feedback! This data has been recorded to train our platform.
            </p>
            <button onClick={onClose} className="btn-primary w-full py-2 font-semibold">
              OK
            </button>
          </div>
        )}

      </div>
    </div>
  )
}
