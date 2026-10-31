import React from 'react';

export default function InfoModal({ type, isOpen, onClose }) {
  if (!isOpen || !type) return null;

  const contentMap = {
    about: {
      title: 'About Azentio Bank',
      subtitle: 'Building the Future of Digital & Commercial Banking Since 2012',
      body: (
        <div className="info-body">
          <p>
            Azentio Bank is a premier digital banking institution chartered to provide enterprise-grade,
            transparent, and frictionless financial services to over 2.4 million retail and business customers worldwide.
          </p>
          <h4>Our Core Commitments</h4>
          <ul>
            <li><strong>Institutional Integrity:</strong> Fully regulated and licensed with capital adequacy exceeding central regulatory benchmarks.</li>
            <li><strong>Zero Hidden Fees:</strong> Complete transparency in fee schedules, interest accruals, and transaction settlement rates.</li>
            <li><strong>Always-On Architecture:</strong> 24/7/365 uninterrupted availability for domestic and international wires, UPI routing, and card clearinghouse operations.</li>
          </ul>
          <h4>Leadership & Compliance</h4>
          <p>
            Headquartered in the global financial district, Azentio operates under stringent compliance frameworks including
            anti-money laundering (AML), Know Your Customer (KYC), and Bank Secrecy Act standards. All deposits are protected
            by central deposit insurance corporations up to $250,000 per depositor.
          </p>
        </div>
      ),
    },
    terms: {
      title: 'Terms & Conditions of Banking Services',
      subtitle: 'Customer Account Agreement & Operating Policies',
      body: (
        <div className="info-body">
          <p>
            By opening or maintaining an account with Azentio Bank, you acknowledge and agree to abide by the
            terms governing deposit accounts, electronic fund transfers (EFT), contactless card processing, UPI settlements, and credit facilities.
          </p>
          <h4>1. Account Maintenance & Opening</h4>
          <p>
            Customers must provide verified government identification. Azentio Bank reserves the right to review, approve,
            or decline account opening requests in accordance with statutory compliance and prudential risk guidelines.
          </p>
          <h4>2. Electronic Fund Transfers & UPI Payments</h4>
          <p>
            All electronic fund transfers, RTGS/NEFT/IMPS transfers, and Unified Payments Interface (UPI) instructions
            received via authenticated credentials are executed with immediate irrevocable settlement once processed.
          </p>
          <h4>3. Cardholder Liabilities & Dispute Settlement</h4>
          <p>
            Cardholders are protected by Zero-Liability policies for unauthorized debit or credit transactions reported within
            48 hours of occurrence. Customers may freeze lost or compromised cards immediately via the digital portal.
          </p>
          <h4>4. Loans & EMI Obligations</h4>
          <p>
            EMI payments are debited automatically on the designated statement cycle due date. Prepayments and foreclosures
            are supported with zero penalty fees on selected personal and gadget finance accounts.
          </p>
        </div>
      ),
    },
    security: {
      title: 'Bank-Grade Security Standards',
      subtitle: 'Multi-Layered Encryption, Real-Time Fraud Shield, & Biometrics',
      body: (
        <div className="info-body">
          <p>
            At Azentio Bank, security is woven into every transaction. We utilize military-grade 256-bit AES encryption
            for data in transit and at rest, coupled with real-time biometric and behavioural threat monitoring.
          </p>
          <h4>Security Protections in Effect</h4>
          <ul>
            <li><strong>256-Bit SSL/TLS Encryption:</strong> Every communication between your device and bank core servers is shielded against eavesdropping.</li>
            <li><strong>Immediate Card Controls:</strong> Freeze, lock, or limit daily ATM and POS transactions in one tap from your card management screen.</li>
            <li><strong>Behavioral Anomaly Detection:</strong> Machine learning algorithms cross-reference abnormal geographical and velocity patterns to block fraudulent attempts before funds leave your account.</li>
            <li><strong>Deposit Guarantee:</strong> Your retail deposits are federally insured up to standard statutory ceilings ($250,000 per individual entity).</li>
          </ul>
        </div>
      ),
    },
  };

  const activeContent = contentMap[type] || contentMap.about;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="info-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>{activeContent.title}</h3>
            <p className="modal-subtitle">{activeContent.subtitle}</p>
          </div>
          <button className="btn-modal-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="info-modal-scroll">
          {activeContent.body}
        </div>
        <div className="modal-footer">
          <button className="btn-primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

