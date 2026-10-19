import React, { createContext, useContext, useState, useCallback } from 'react';
import '../styles/modal.css';

const ModalContext = createContext(null);

export function ModalProvider({ children }) {
  const [modal, setModal] = useState(null);

  const showAlert = useCallback((message, options = {}) => {
    return new Promise((resolve) => {
      setModal({
        mode: 'alert',
        title: options.title || 'Notification',
        message,
        variant: options.variant || 'info',
        confirmText: options.confirmText || 'OK',
        onConfirm: () => {
          setModal(null);
          resolve(true);
        },
      });
    });
  }, []);

  const showConfirm = useCallback((message, options = {}) => {
    return new Promise((resolve) => {
      setModal({
        mode: 'confirm',
        title: options.title || 'Confirmation',
        message,
        variant: options.variant || 'danger',
        confirmText: options.confirmText || 'Yes, Continue',
        cancelText: options.cancelText || 'Cancel',
        onConfirm: () => {
          setModal(null);
          resolve(true);
        },
        onCancel: () => {
          setModal(null);
          resolve(false);
        },
      });
    });
  }, []);

  const renderIcon = (variant) => {
    if (variant === 'success') return '✓';
    if (variant === 'danger' || variant === 'confirm') return '!';
    if (variant === 'warning') return '⚠';
    return 'i';
  };

  return (
    <ModalContext.Provider value={{ showAlert, showConfirm }}>
      {children}
      {modal && (
        <div
          className="custom-modal-overlay"
          onClick={() => {
            if (modal.mode === 'confirm') modal.onCancel();
            else modal.onConfirm();
          }}
        >
          <div
            className="custom-modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            <div className={`custom-modal-icon ${modal.variant}`}>
              {renderIcon(modal.variant)}
            </div>
            <h3 className="custom-modal-title">{modal.title}</h3>
            <p className="custom-modal-message">{modal.message}</p>
            <div className="custom-modal-actions">
              {modal.mode === 'confirm' && (
                <button
                  type="button"
                  className="custom-modal-btn cancel"
                  onClick={modal.onCancel}
                >
                  {modal.cancelText}
                </button>
              )}
              <button
                type="button"
                className={`custom-modal-btn ${
                  modal.variant === 'danger' ? 'danger' : 'primary'
                }`}
                onClick={modal.onConfirm}
              >
                {modal.confirmText}
              </button>
            </div>
          </div>
        </div>
      )}
    </ModalContext.Provider>
  );
}

export function useModal() {
  return useContext(ModalContext);
}
