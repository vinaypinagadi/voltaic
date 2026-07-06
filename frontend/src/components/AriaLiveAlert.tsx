import React, { useEffect, useState } from 'react';

interface AriaLiveAlertProps {
  message: string;
  type?: 'polite' | 'assertive';
}

export const AriaLiveAlert: React.FC<AriaLiveAlertProps> = ({ message, type = 'polite' }) => {
  const [announcement, setAnnouncement] = useState('');

  useEffect(() => {
    if (message) {
      setAnnouncement(message);
      // Clear after a short delay so that repeated identical alerts can be announced again
      const timer = setTimeout(() => setAnnouncement(''), 3000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  return (
    <div 
      className="visually-hidden" 
      role="status" 
      aria-live={type} 
      aria-atomic="true"
    >
      {announcement}
    </div>
  );
};
export default AriaLiveAlert;
