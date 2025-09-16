import React from 'react';
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../Dialog';

interface PayloadModalProps {
  isOpen: boolean;
  onClose: () => void;
  payload: any;
  eventId?: number;
}

export function PayloadModal({ isOpen, onClose, payload, eventId }: PayloadModalProps) {
  if (!payload) return null;

  const formatPayload = (rawPayload: string) => {
    try {
      const parsed = JSON.parse(rawPayload);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return rawPayload;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Webhook Payload</DialogTitle>
          <DialogDescription>
            Raw webhook payload for event {eventId}
          </DialogDescription>
        </DialogHeader>
        <div className="mt-4">
          <pre className="bg-gray-100 p-4 rounded-lg text-sm overflow-x-auto">
            {formatPayload(payload)}
          </pre>
        </div>
      </DialogContent>
    </Dialog>
  );
}
