import * as React from "react";
import { Button } from "../Button";
import { Input } from "../Input";
import { Checkbox } from "../Checkbox";
import { api } from "../../lib/api.ts";
import { useState, useEffect } from "react";

type Props = { 
  open: boolean; 
  onOpenChange: (v: boolean) => void; 
  onCreated: () => void; 
  accountId?: string; // Optional account ID for pre-selection
};

export function ActivityCreateModal({ open, onOpenChange, onCreated, accountId }: Props) {
  const [type, setType] = useState("call");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [dealId, setDealId] = useState("");
  const [contactId, setContactId] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [completed, setCompleted] = useState(false);
  const [deals, setDeals] = useState<any[]>([]);
  const [contacts, setContacts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      Promise.all([
        api.get("/deals/").then(setDeals),
        api.get("/contacts/").then(setContacts)
      ]).catch(console.error);
    }
  }, [open]);

  async function handleCreate() {
    setErr(null);
    if (!subject.trim()) { setErr("Activity subject is required."); return; }
    
    setLoading(true);
    try {
      // Extract just the date part from the datetime string
      const dueDateOnly = dueDate ? dueDate.split('T')[0] : null;
      
      await api.post("/activities/", { 
        type, 
        subject, 
        description, 
        deal_id: dealId || null,
        contact_id: contactId || null,
        due_date: dueDateOnly,
        completed
      });
      onOpenChange(false);
      setType("call"); setSubject(""); setDescription(""); setDealId(""); setContactId(""); setDueDate(""); setCompleted(false);
      onCreated();
    } catch (e: any) {
      setErr(e.message || "Failed to create activity.");
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/60 backdrop-blur-[2px]" onClick={() => onOpenChange(false)} />
      
      <div className="relative bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg mx-4">
        <div className="mb-4">
          <h2 className="text-xl font-semibold">Create New Activity</h2>
          <p className="text-gray-600 text-sm">Add a new activity to your CRM system</p>
        </div>

        {err && <div className="text-red-600 text-sm mb-4 p-2 bg-red-50 rounded">{err}</div>}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Type</label>
            <select 
              value={type} 
              onChange={(e) => setType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="call">Call</option>
              <option value="email">Email</option>
              <option value="meeting">Meeting</option>
              <option value="task">Task</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Subject*</label>
            <Input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Enter activity subject" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea 
              value={description} 
              onChange={(e) => setDescription(e.target.value)} 
              placeholder="Describe this activity..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[80px]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Deal</label>
            <select 
              value={dealId} 
              onChange={(e) => setDealId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a deal</option>
              {deals.map(deal => (
                <option key={deal.id} value={deal.id}>{deal.title}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Contact</label>
            <select 
              value={contactId} 
              onChange={(e) => setContactId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select a contact</option>
              {contacts.map(contact => (
                <option key={contact.id} value={contact.id}>{contact.first_name} {contact.last_name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Due Date</label>
            <Input value={dueDate} onChange={(e) => setDueDate(e.target.value)} type="datetime-local" />
            <p className="text-xs text-gray-500">Select your date and time, then click "Create Activity" below to save</p>
          </div>
          <div className="flex items-center space-x-2">
            <input 
              type="checkbox" 
              checked={completed} 
              onChange={(e) => setCompleted(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label className="text-sm font-medium">Completed</label>
          </div>
        </div>

        <div className="flex justify-end space-x-2 mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>Cancel</Button>
          <Button onClick={handleCreate} disabled={loading}>
            {loading ? "Creating…" : "Create Activity"}
          </Button>
        </div>
      </div>
    </div>
  );
}
