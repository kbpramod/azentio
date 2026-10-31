import React, { useState, useEffect } from 'react';
import { bankingApi } from '../services/api';

export default function EmiView({ user, onPaymentCompleted }) {
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [payingLoanId, setPayingLoanId] = useState(null);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Loan Calculator State
  const [calcAmount, setCalcAmount] = useState(250000);
  const [calcTenure, setCalcTenure] = useState(24);
  const [calcRate, setCalcRate] = useState(10.5);

  const loadLoans = async () => {
    try {
      const data = await bankingApi.getLoans();
      setLoans(data);
    } catch (err) {
      console.error('Failed to load loans', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLoans();
  }, []);

  const handlePayEmi = async (loanId, amount) => {
    setPayingLoanId(loanId);
    setMessage({ type: '', text: '' });

    try {
      const res = await bankingApi.payEmi(loanId, amount);
      setMessage({ type: 'success', text: res.message });
      loadLoans();
      if (onPaymentCompleted) {
        onPaymentCompleted();
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message || 'Payment failed.' });
    } finally {
      setPayingLoanId(null);
    }
  };

  // Monthly EMI Calculation formula: P * r * (1+r)^n / ((1+r)^n - 1)
  const monthlyRate = calcRate / 12 / 100;
  const calculatedEmi = Math.round(
    (calcAmount * monthlyRate * Math.pow(1 + monthlyRate, calcTenure)) /
      (Math.pow(1 + monthlyRate, calcTenure) - 1)
  );
  const totalPayable = calculatedEmi * calcTenure;
  const totalInterest = totalPayable - calcAmount;

  return (
    <div className="emi-view-container">
      {message.text && (
        <div className={`emi-banner ${message.type}`}>{message.text}</div>
      )}

      {/* Active Loans & EMI Tracker */}
      <div className="active-loans-section">
        <div className="section-title-row">
          <div>
            <h3>Active Loans & EMI Facilities</h3>
            <p className="subtitle">Real-time status synced from Azentio Core Banking Database</p>
          </div>
          <span className="loans-count-pill">{loans.length} Active Loans</span>
        </div>

        {loading ? (
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>Retrieving active loan accounts & schedules...</p>
          </div>
        ) : loans.length === 0 ? (
          <div className="empty-state">
            <p>No active loan facilities found on your customer profile.</p>
          </div>
        ) : (
          <div className="loans-cards-grid">
            {loans.map((loan) => {
              const progressPct = Math.min(
                100,
                Math.round(((loan.principal - loan.outstanding) / loan.principal) * 100)
              );

              return (
                <div key={loan.loan_id} className="loan-card">
                  <div className="loan-card-top">
                    <div>
                      <span className="loan-product-title">{loan.product}</span>
                      <span className="loan-id-tag">{loan.loan_id}</span>
                    </div>
                    <span className="loan-status-active">● {loan.status}</span>
                  </div>

                  <div className="loan-balances-grid">
                    <div className="bal-col">
                      <span className="bal-label">Outstanding Principal</span>
                      <strong className="bal-val">₹{loan.outstanding.toLocaleString()}</strong>
                    </div>
                    <div className="bal-col">
                      <span className="bal-label">Sanctioned Amount</span>
                      <span className="bal-val-sub">₹{loan.principal.toLocaleString()}</span>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="loan-progress-box">
                    <div className="progress-labels">
                      <span>Repaid: {progressPct}%</span>
                      <span>Next Due: {new Date(loan.next_due_date).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                    </div>
                    <div className="progress-bar-track">
                      <div className="progress-bar-fill" style={{ width: `${progressPct}%` }}></div>
                    </div>
                  </div>

                  <div className="loan-card-footer">
                    <div>
                      <span className="emi-label">Monthly EMI Due</span>
                      <strong className="emi-amount">₹{loan.emi_amount.toLocaleString()}</strong>
                    </div>

                    <button
                      className="btn-pay-emi"
                      disabled={payingLoanId === loan.loan_id || loan.outstanding <= 0}
                      onClick={() => handlePayEmi(loan.loan_id, loan.emi_amount)}
                    >
                      {payingLoanId === loan.loan_id ? (
                        <span className="loading-spinner"></span>
                      ) : loan.outstanding <= 0 ? (
                        'Fully Paid'
                      ) : (
                        'Pay Next EMI'
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Instant Loan Eligibility Calculator */}
      <div className="emi-calc-card">
        <div className="calc-header">
          <div>
            <h4>Instant Personal Loan Calculator</h4>
            <p>Pre-approved rates starting at 10.5% p.a. with zero prepayment fees</p>
          </div>
          <span className="calc-badge">Instant Disbursal</span>
        </div>

        <div className="calc-split">
          <div className="calc-sliders-col">
            <div className="slider-group">
              <div className="slider-label-row">
                <span>Required Loan Amount</span>
                <strong>₹{calcAmount.toLocaleString()}</strong>
              </div>
              <input
                type="range"
                min="50000"
                max="1500000"
                step="25000"
                value={calcAmount}
                onChange={(e) => setCalcAmount(Number(e.target.value))}
              />
              <div className="slider-ticks">
                <span>₹50K</span>
                <span>₹7.5L</span>
                <span>₹15L</span>
              </div>
            </div>

            <div className="slider-group">
              <div className="slider-label-row">
                <span>Tenure Duration</span>
                <strong>{calcTenure} Months ({calcTenure / 12} Yrs)</strong>
              </div>
              <input
                type="range"
                min="6"
                max="60"
                step="6"
                value={calcTenure}
                onChange={(e) => setCalcTenure(Number(e.target.value))}
              />
              <div className="slider-ticks">
                <span>6M</span>
                <span>24M</span>
                <span>60M</span>
              </div>
            </div>
          </div>

          <div className="calc-result-box">
            <span className="res-label">Calculated Monthly Installment</span>
            <div className="res-emi-number">₹{calculatedEmi.toLocaleString()} / mo</div>

            <div className="res-breakdown">
              <div className="res-row">
                <span>Principal Amount:</span>
                <strong>₹{calcAmount.toLocaleString()}</strong>
              </div>
              <div className="res-row">
                <span>Total Interest Payable:</span>
                <strong>₹{totalInterest.toLocaleString()}</strong>
              </div>
              <div className="res-row total">
                <span>Total Repayment:</span>
                <strong>₹{totalPayable.toLocaleString()}</strong>
              </div>
            </div>

            <button
              className="btn-primary btn-apply-loan"
              onClick={() => setMessage({ type: 'success', text: `Pre-approved application for ₹${calcAmount.toLocaleString()} submitted to branch credit officer.` })}
            >
              Apply for Pre-Approved Loan
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

