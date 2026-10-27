import React, { useState } from 'react';
import { 
  CheckCircle2, 
  AlertCircle, 
  FileText, 
  Upload, 
  ImageIcon, 
  RefreshCw, 
  Check, 
  X, 
  Send,
  Flag,
  FileCheck,
  Code,
  Terminal,
  Info
} from 'lucide-react';
import { api } from '../api';

export default function ContentStudio({ 
  orgId, 
  activeRole, 
  onReviewCreated, 
  presets = [] 
}) {
  const [title, setTitle] = useState('Q4 Product Announcement');
  const [channel, setChannel] = useState('LinkedIn post');
  const [content, setContent] = useState(
    'We are thrilled to announce that the tool is now used by over 5 million customers worldwide! Our platform offers 100% secure infrastructure and guaranteed uptime, making it a revolutionary solution for modern enterprises. Check out this killer feature and sign up today!'
  );
  const [useAi, setUseAi] = useState(true);
  const [contentType, setContentType] = useState('text'); // text | file | image

  // Image states
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [imageAlt, setImageAlt] = useState('');

  // Document upload state
  const [uploadFileObj, setUploadFileObj] = useState(null);

  // Scan state
  const [scanning, setScanning] = useState(false);
  const [reviewResult, setReviewResult] = useState(null);
  const [activeFilter, setActiveFilter] = useState('all');
  const [dismissModalFinding, setDismissModalFinding] = useState(null);
  const [dismissReason, setDismissReason] = useState('');
  const [submissionSuccess, setSubmissionSuccess] = useState(false);

  // Load sample test case
  const handleSelectPreset = (presetId) => {
    const selected = presets.find(p => p.id === presetId);
    if (!selected) return;
    setTitle(selected.title);
    setChannel(selected.channel);
    setContent(selected.text);
    setContentType('text');
    setReviewResult(null);
  };

  // Run linter / review
  const handleRunReview = async () => {
    setScanning(true);
    setSubmissionSuccess(false);
    try {
      if (contentType === 'text') {
        const res = await api.reviewText(orgId, {
          text: content,
          title: title || 'Untitled Content',
          channel,
          creator_name: 'Maya (Content Creator)',
          use_ai: useAi,
        });
        setReviewResult(res);
      } else if (contentType === 'image') {
        if (!imageFile) throw new Error('Select an image file first.');
        const fd = new FormData();
        fd.append('image', imageFile);
        fd.append('alt_text', imageAlt);
        const res = await api.reviewImage(orgId, fd);
        setReviewResult(res);
      } else if (contentType === 'file') {
        if (!uploadFileObj) throw new Error('Select a document (.docx, .pdf, .txt, .md).');
        const fd = new FormData();
        fd.append('file', uploadFileObj);
        fd.append('title', title);
        fd.append('channel', channel);
        fd.append('use_ai', String(useAi));
        const res = await api.reviewFile(orgId, fd);
        setReviewResult(res);
      }
    } catch (err) {
      alert(`Lint check failed: ${err.message}`);
    } finally {
      setScanning(false);
    }
  };

  // 1-Click Apply Fix
  const handleAcceptFix = async (finding) => {
    if (!finding.suggestion || !reviewResult) return;
    
    let newContent = content;
    if (finding.original && content.includes(finding.original)) {
      newContent = content.replace(finding.original, finding.suggestion);
    }
    setContent(newContent);

    if (finding.id) {
      try {
        await api.decideFinding(finding.id, { status: 'accepted' });
      } catch (err) {
        console.error('Failed to update decision', err);
      }
    }

    setReviewResult(prev => ({
      ...prev,
      findings: prev.findings.map(f => f.id === finding.id ? { ...f, status: 'accepted' } : f)
    }));
  };

  // Dismiss with rationale
  const handleConfirmDismiss = async () => {
    if (!dismissModalFinding) return;
    if (!dismissReason.trim()) {
      alert('A technical rationale is required to dismiss a rule.');
      return;
    }
    try {
      if (dismissModalFinding.id) {
        await api.decideFinding(dismissModalFinding.id, {
          status: 'dismissed',
          reason: dismissReason,
        });
      }
      setReviewResult(prev => ({
        ...prev,
        findings: prev.findings.map(f => f.id === dismissModalFinding.id ? { ...f, status: 'dismissed', dismiss_reason: dismissReason } : f)
      }));
      setDismissModalFinding(null);
      setDismissReason('');
    } catch (err) {
      alert(`Dismiss failed: ${err.message}`);
    }
  };

  // Report false alarm
  const handleFlagIncorrect = async (finding) => {
    if (!finding.id) return;
    try {
      await api.decideFinding(finding.id, {
        status: 'dismissed',
        reason: 'Reported as false positive by engineer/author',
        incorrect_finding: true,
      });
      setReviewResult(prev => ({
        ...prev,
        findings: prev.findings.map(f => f.id === finding.id ? { ...f, status: 'dismissed', incorrect_finding: true } : f)
      }));
    } catch (err) {
      alert(`Report failed: ${err.message}`);
    }
  };

  // Submit to Review Pipeline
  const handleSubmitForApproval = async () => {
    if (!reviewResult || !reviewResult.review_id) {
      alert('Run a lint check before submitting for approval.');
      return;
    }
    try {
      await api.updateWorkflow(reviewResult.review_id, {
        action: 'submit_for_review',
        actor_name: 'Maya (Content Creator)',
        actor_role: 'creator',
        notes: 'Submitted for peer/manager brand review.',
      });
      setSubmissionSuccess(true);
      if (onReviewCreated) onReviewCreated();
    } catch (err) {
      alert(`Submission failed: ${err.message}`);
    }
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => setImagePreview(reader.result);
      reader.readAsDataURL(file);
    }
  };

  const findingsList = reviewResult ? (reviewResult.findings || []) : [];
  const openFindings = findingsList.filter(f => f.status === 'open');
  const resolvedFindings = findingsList.filter(f => f.status === 'accepted' || f.status === 'dismissed');

  const filteredFindings = findingsList.filter(f => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'open') return f.status === 'open';
    if (activeFilter === 'resolved') return f.status !== 'open';
    if (activeFilter === 'claims') return f.category === 'claim';
    if (activeFilter === 'terms') return f.category === 'terminology' || f.category === 'banned_phrase';
    if (activeFilter === 'accessibility') return f.category === 'alt_text' || f.category === 'contrast';
    return true;
  });

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '20px' }}>
      {/* Top Action Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        marginBottom: '16px',
        borderBottom: '1px solid var(--border-subtle)',
        paddingBottom: '14px',
      }}>
        <div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-main)', letterSpacing: '-0.02em' }}>
            Content Policy Linter
          </h1>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', marginTop: '2px' }}>
            Pre-publication static analysis against terminology dictionaries, dated fact sheets, and WCAG rules.
          </div>
        </div>

        {/* Test Case Picker */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
            Load test case:
          </span>
          <select 
            id="preset-picker-select"
            onChange={(e) => handleSelectPreset(e.target.value)}
            style={{
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-main)',
              padding: '5px 10px',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.78rem',
              cursor: 'pointer',
              outline: 'none',
              fontFamily: 'var(--font-sans)',
            }}
          >
            <option value="">Select test scenario...</option>
            {presets.map(p => (
              <option key={p.id} value={p.id}>{p.title}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Studio Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1.1fr) minmax(0, 1fr)',
        gap: '16px',
        alignItems: 'start',
      }}>
        {/* Left Column: Editor & Controls */}
        <div className="glass-panel" style={{ padding: '16px' }}>
          {/* Metadata Controls */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 160px', gap: '10px', marginBottom: '12px' }}>
            <div>
              <label style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', display: 'block', marginBottom: '4px' }}>
                Document Title
              </label>
              <input
                id="content-title-input"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Q4 Launch Announcement"
                style={{
                  width: '100%',
                  padding: '6px 10px',
                  fontSize: '0.8125rem',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', display: 'block', marginBottom: '4px' }}>
                Channel / Format
              </label>
              <select
                id="content-channel-select"
                value={channel}
                onChange={(e) => setChannel(e.target.value)}
                style={{
                  width: '100%',
                  padding: '6px 10px',
                  fontSize: '0.8125rem',
                }}
              >
                <option value="LinkedIn post">LinkedIn post</option>
                <option value="Blog article">Blog article</option>
                <option value="Press release">Press release</option>
                <option value="Email newsletter">Email newsletter</option>
                <option value="Web Banner">Web Banner (HTML)</option>
                <option value="Social Ad">Social Ad</option>
              </select>
            </div>
          </div>

          {/* Format Selector */}
          <div style={{
            display: 'flex',
            gap: '4px',
            marginBottom: '10px',
            borderBottom: '1px solid var(--border-subtle)',
            paddingBottom: '8px',
          }}>
            {[
              { id: 'text', label: 'Plain / HTML' },
              { id: 'file', label: 'Document (.docx / .pdf)' },
              { id: 'image', label: 'Image Asset' },
            ].map(tab => (
              <button
                key={tab.id}
                id={`type-tab-${tab.id}`}
                onClick={() => setContentType(tab.id)}
                style={{
                  padding: '4px 10px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.75rem',
                  fontWeight: 500,
                  border: 'none',
                  cursor: 'pointer',
                  background: contentType === tab.id ? 'var(--bg-tertiary)' : 'transparent',
                  color: contentType === tab.id ? 'var(--text-main)' : 'var(--text-dim)',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Content Inputs */}
          {contentType === 'text' && (
            <div>
              <textarea
                id="content-text-editor"
                rows={11}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Enter or paste draft content..."
                style={{
                  width: '100%',
                  padding: '12px',
                  fontSize: '0.85rem',
                  lineHeight: '1.55',
                  fontFamily: 'var(--font-mono)',
                  resize: 'vertical',
                }}
              />

              {/* Character stats & AI option */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginTop: '8px',
                fontSize: '0.75rem',
                color: 'var(--text-dim)',
                fontFamily: 'var(--font-mono)',
              }}>
                <div>
                  {content.length} chars | {content.trim().split(/\s+/).filter(Boolean).length} words
                </div>

                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontFamily: 'var(--font-sans)' }}>
                  <input
                    type="checkbox"
                    checked={useAi}
                    onChange={(e) => setUseAi(e.target.checked)}
                    style={{ cursor: 'pointer' }}
                  />
                  <span>Semantic analysis (Gemini)</span>
                </label>
              </div>
            </div>
          )}

          {contentType === 'file' && (
            <div style={{
              padding: '24px',
              border: '1px dashed var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              textAlign: 'center',
              background: 'var(--bg-input)',
            }}>
              <Upload size={28} color="#64748b" style={{ margin: '0 auto 8px auto' }} />
              <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '2px' }}>
                Select File
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginBottom: '12px' }}>
                Accepts .docx, .pdf, .txt, .md
              </div>
              <input
                id="file-upload-input"
                type="file"
                accept=".docx,.pdf,.txt,.md"
                onChange={(e) => setUploadFileObj(e.target.files[0])}
                style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}
              />
              {uploadFileObj && (
                <div style={{ marginTop: '10px', fontSize: '0.75rem', color: '#4ade80', fontFamily: 'var(--font-mono)' }}>
                  {uploadFileObj.name} ({(uploadFileObj.size / 1024).toFixed(1)} KB)
                </div>
              )}
            </div>
          )}

          {contentType === 'image' && (
            <div>
              <div style={{
                padding: '20px',
                border: '1px dashed var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                textAlign: 'center',
                background: 'var(--bg-input)',
                marginBottom: '10px',
              }}>
                {imagePreview ? (
                  <img 
                    src={imagePreview} 
                    alt="Preview" 
                    style={{ maxHeight: '140px', borderRadius: 'var(--radius-sm)', margin: '0 auto 8px auto', display: 'block' }} 
                  />
                ) : (
                  <ImageIcon size={28} color="#64748b" style={{ margin: '0 auto 8px auto' }} />
                )}
                <input
                  id="image-upload-input"
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={handleImageChange}
                  style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', display: 'block', marginBottom: '4px' }}>
                  Alt-Text Attribute
                </label>
                <input
                  id="image-alt-input"
                  type="text"
                  value={imageAlt}
                  onChange={(e) => setImageAlt(e.target.value)}
                  placeholder="e.g. Dashboard metrics overview"
                  style={{ width: '100%', padding: '6px 10px', fontSize: '0.8125rem' }}
                />
              </div>
            </div>
          )}

          {/* Action Row */}
          <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
            <button
              id="run-review-btn"
              onClick={handleRunReview}
              disabled={scanning}
              className="btn btn-primary"
              style={{ flex: 1 }}
            >
              {scanning ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  <span>Linting Content...</span>
                </>
              ) : (
                <>
                  <FileCheck size={14} />
                  <span>Run Policy Check</span>
                </>
              )}
            </button>

            {reviewResult && (
              <button
                id="submit-approval-btn"
                onClick={handleSubmitForApproval}
                className="btn btn-secondary"
              >
                <Send size={13} />
                <span>Submit to Pipeline</span>
              </button>
            )}
          </div>

          {submissionSuccess && (
            <div style={{
              marginTop: '12px',
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(74, 222, 128, 0.08)',
              border: '1px solid rgba(74, 222, 128, 0.25)',
              color: '#4ade80',
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}>
              <CheckCircle2 size={14} />
              <span>Draft submitted to Review Pipeline. Assigned to Manager.</span>
            </div>
          )}
        </div>

        {/* Right Column: Linter Output & Findings */}
        <div>
          {!reviewResult ? (
            <div className="glass-panel" style={{ padding: '36px 20px', textAlign: 'center' }}>
              <Terminal size={24} color="#64748b" style={{ margin: '0 auto 10px auto' }} />
              <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
                Linter Output
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', maxWidth: '340px', margin: '0 auto 16px auto' }}>
                Execute "Run Policy Check" or load a test case to inspect terminology rules, verified facts, and accessibility.
              </div>
              <div style={{
                textAlign: 'left',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-subtle)',
                padding: '10px 14px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.72rem',
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-dim)',
              }}>
                <div>[1] Exact rules : terminology, banned phrases, WCAG contrast</div>
                <div>[2] Claim verifier: numerical match against fact sheet</div>
                <div>[3] Grounded LLM  : tone review with strict passage validation</div>
              </div>
            </div>
          ) : (
            <div className="glass-panel" style={{ padding: '16px' }}>
              {/* Status Header */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingBottom: '12px',
                borderBottom: '1px solid var(--border-subtle)',
                marginBottom: '12px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.875rem', fontWeight: 600 }}>Findings</span>
                  <span className={`badge ${openFindings.length === 0 ? 'badge-success' : 'badge-high'}`}>
                    {openFindings.length === 0 ? 'PASSED' : `${openFindings.length} ISSUES`}
                  </span>
                </div>

                <div style={{ display: 'flex', gap: '4px', fontFamily: 'var(--font-mono)', fontSize: '0.6875rem' }}>
                  <span className="badge badge-high">{findingsList.filter(f => f.severity === 'high').length} High</span>
                  <span className="badge badge-medium">{findingsList.filter(f => f.severity === 'medium').length} Med</span>
                  <span className="badge badge-low">{findingsList.filter(f => f.severity === 'low').length} Low</span>
                </div>
              </div>

              {/* Filters */}
              <div style={{
                display: 'flex',
                gap: '4px',
                overflowX: 'auto',
                paddingBottom: '6px',
                marginBottom: '10px',
                fontSize: '0.72rem',
              }}>
                {[
                  { id: 'all', label: `All (${findingsList.length})` },
                  { id: 'open', label: `Open (${openFindings.length})` },
                  { id: 'resolved', label: `Resolved (${resolvedFindings.length})` },
                  { id: 'claims', label: 'Claims' },
                  { id: 'terms', label: 'Terms' },
                  { id: 'accessibility', label: 'Accessibility' },
                ].map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveFilter(tab.id)}
                    style={{
                      background: activeFilter === tab.id ? 'var(--bg-tertiary)' : 'transparent',
                      border: '1px solid',
                      borderColor: activeFilter === tab.id ? 'var(--border-hover)' : 'transparent',
                      color: activeFilter === tab.id ? 'var(--text-main)' : 'var(--text-dim)',
                      padding: '3px 8px',
                      borderRadius: 'var(--radius-sm)',
                      cursor: 'pointer',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Findings List */}
              {filteredFindings.length === 0 ? (
                <div style={{
                  padding: '24px',
                  textAlign: 'center',
                  background: 'var(--bg-input)',
                  borderRadius: 'var(--radius-sm)',
                  color: '#4ade80',
                  fontSize: '0.8rem',
                }}>
                  <CheckCircle2 size={20} style={{ margin: '0 auto 6px auto' }} />
                  <div>No issues detected in this category.</div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '460px', overflowY: 'auto' }}>
                  {filteredFindings.map((finding, idx) => {
                    const isAccepted = finding.status === 'accepted';
                    const isDismissed = finding.status === 'dismissed';

                    return (
                      <div
                        key={finding.id || idx}
                        id={`finding-card-${finding.id || idx}`}
                        style={{
                          background: 'var(--bg-input)',
                          border: '1px solid',
                          borderColor: isAccepted ? 'rgba(74, 222, 128, 0.25)' : isDismissed ? 'rgba(148, 163, 184, 0.15)' : 'var(--border-subtle)',
                          borderRadius: 'var(--radius-sm)',
                          padding: '10px 12px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span className={`badge badge-${finding.severity || 'low'}`}>
                              {finding.severity?.toUpperCase()}
                            </span>
                            <span style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                              {finding.rule_id}
                            </span>
                          </div>

                          {isAccepted && (
                            <span className="badge badge-success">
                              <Check size={11} /> FIXED
                            </span>
                          )}
                          {isDismissed && (
                            <span className="badge" style={{ background: 'rgba(148, 163, 184, 0.1)', color: '#94a3b8' }}>
                              DISMISSED {finding.incorrect_finding ? '(FALSE POSITIVE)' : ''}
                            </span>
                          )}
                        </div>

                        {/* Message */}
                        <div style={{ fontSize: '0.8125rem', color: 'var(--text-main)', marginBottom: '4px' }}>
                          {finding.message}
                        </div>

                        {/* Original String */}
                        {finding.original && (
                          <div style={{
                            fontSize: '0.75rem',
                            color: '#f87171',
                            background: 'rgba(248, 113, 113, 0.08)',
                            padding: '2px 6px',
                            borderRadius: 'var(--radius-sm)',
                            display: 'inline-block',
                            marginBottom: '6px',
                            fontFamily: 'var(--font-mono)',
                          }}>
                            "{finding.original}"
                          </div>
                        )}

                        {/* Evidence */}
                        {finding.evidence && Object.keys(finding.evidence).length > 0 && (
                          <div style={{
                            fontSize: '0.72rem',
                            color: 'var(--text-muted)',
                            background: 'rgba(0,0,0,0.2)',
                            padding: '4px 8px',
                            borderRadius: 'var(--radius-sm)',
                            marginBottom: '6px',
                            fontFamily: 'var(--font-mono)',
                          }}>
                            {finding.evidence.source && <span>[{finding.evidence.source}] </span>}
                            {finding.evidence.fact && <span>{finding.evidence.fact} </span>}
                            {finding.evidence.rule_text && <span>{finding.evidence.rule_text} </span>}
                            {finding.evidence.ratio && <span>Measured contrast {finding.evidence.ratio}:1 (WCAG AA min 4.5:1)</span>}
                          </div>
                        )}

                        {/* Fix Suggestion */}
                        {finding.suggestion && (
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            background: 'rgba(74, 222, 128, 0.06)',
                            border: '1px solid rgba(74, 222, 128, 0.15)',
                            padding: '6px 10px',
                            borderRadius: 'var(--radius-sm)',
                            marginTop: '6px',
                          }}>
                            <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#dcfce7' }}>
                              Fix: "{finding.suggestion}"
                            </div>

                            {!isAccepted && !isDismissed && (
                              <button
                                id={`accept-fix-btn-${finding.id || idx}`}
                                onClick={() => handleAcceptFix(finding)}
                                className="btn btn-sm btn-success"
                                style={{ padding: '2px 8px', fontSize: '0.6875rem' }}
                              >
                                Apply Fix
                              </button>
                            )}
                          </div>
                        )}

                        {/* Dismissal / feedback */}
                        {!isAccepted && !isDismissed && (
                          <div style={{ display: 'flex', gap: '6px', marginTop: '8px', justifyContent: 'flex-end' }}>
                            <button
                              id={`dismiss-btn-${finding.id || idx}`}
                              onClick={() => {
                                setDismissModalFinding(finding);
                                setDismissReason('');
                              }}
                              className="btn btn-sm btn-secondary"
                              style={{ fontSize: '0.6875rem', padding: '2px 6px' }}
                            >
                              Dismiss...
                            </button>
                            <button
                              id={`flag-false-alarm-btn-${finding.id || idx}`}
                              onClick={() => handleFlagIncorrect(finding)}
                              className="btn btn-sm btn-secondary"
                              style={{ fontSize: '0.6875rem', padding: '2px 6px', color: 'var(--text-dim)' }}
                              title="Report false positive"
                            >
                              False Positive
                            </button>
                          </div>
                        )}

                        {finding.dismiss_reason && (
                          <div style={{ fontSize: '0.6875rem', color: 'var(--text-dim)', marginTop: '4px', fontStyle: 'italic' }}>
                            Rationale: "{finding.dismiss_reason}"
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Claims Extraction Table */}
              {reviewResult.claims && reviewResult.claims.length > 0 && (
                <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-dim)', marginBottom: '6px' }}>
                    Claims Assertion Table ({reviewResult.claims.length})
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {reviewResult.claims.map((c, i) => {
                      const isSupported = c.verdict === 'supported';
                      const isContradicted = c.verdict === 'contradicted';
                      const badgeClass = isSupported ? 'badge-success' : isContradicted ? 'badge-high' : 'badge-medium';
                      return (
                        <div key={i} style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '4px 8px',
                          background: 'var(--bg-input)',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.72rem',
                          fontFamily: 'var(--font-mono)',
                        }}>
                          <span style={{ color: 'var(--text-main)' }}>"{c.text}"</span>
                          <span className={`badge ${badgeClass}`} style={{ textTransform: 'uppercase' }}>
                            {c.verdict?.replace('_', ' ')}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Dismiss Modal */}
      {dismissModalFinding && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.65)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div className="glass-panel" style={{ width: '400px', padding: '18px', background: 'var(--bg-secondary)' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '6px' }}>
              Dismiss Rule Finding
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
              Specify the rationale for this exception. Tracked for rule calibration and policy review.
            </p>
            <textarea
              rows={3}
              value={dismissReason}
              onChange={(e) => setDismissReason(e.target.value)}
              placeholder="e.g. Quoting client statement verbatim; approved exception."
              style={{
                width: '100%',
                padding: '8px',
                fontSize: '0.8125rem',
                marginBottom: '12px',
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button 
                onClick={() => setDismissModalFinding(null)} 
                className="btn btn-secondary btn-sm"
              >
                Cancel
              </button>
              <button 
                id="confirm-dismiss-btn"
                onClick={handleConfirmDismiss} 
                className="btn btn-primary btn-sm"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
