import * as React from "react";
import { Button } from "../Button";
import { Input } from "../Input";
import { api } from "../../lib/api.ts";
import { useState, useEffect } from "react";

type Props = { 
  open: boolean; 
  onOpenChange: (v: boolean) => void; 
  onCreated: () => void; 
  accountId?: string; // Optional account ID for pre-selection
};

export function DealCreateModal({ open, onOpenChange, onCreated, accountId }: Props) {
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [stage, setStage] = useState("prospecting");
  const [selectedAccountId, setSelectedAccountId] = useState(accountId || "");
  const [contactId, setContactId] = useState("");
  const [closeDate, setCloseDate] = useState("");
  const [accounts, setAccounts] = useState<any[]>([]);
  const [contacts, setContacts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      Promise.all([
        api.get("/accounts/").then(setAccounts),
        api.get("/contacts/").then(setContacts)
      ]).catch(console.error);
      if (accountId) {
        setSelectedAccountId(accountId);
      }
    }
  }, [open, accountId]);

  async function handleCreate() {
    setErr(null);
    if (!title.trim()) { setErr("Deal title is required."); return; }
    if (!amount || isNaN(Number(amount))) { setErr("Valid amount is required."); return; }
    
    setLoading(true);
    try {
      await api.post("/deals/", { 
        title, 
        amount: Number(amount), 
        stage, 
        account_id: selectedAccountId || null,
        contact_id: contactId || null,
        close_date: closeDate ? closeDate.split('T')[0] : null
      });
      onOpenChange(false);
      setTitle(""); setAmount(""); setStage("prospecting"); setAccountId(""); setContactId(""); setCloseDate("");
      onCreated();
    } catch (e: any) {
      setErr(e.message || "Failed to create deal.");
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
          <h2 className="text-xl font-semibold">Create New Deal</h2>
          <p className="text-gray-600 text-sm">Add a new deal to your CRM system</p>
        </div>

        {err && <div className="text-red-600 text-sm mb-4 p-2 bg-red-50 rounded">{err}</div>}

        <div className="space-y-4">
          <div>
            <label htmlFor="deal-title" className="block text-sm font-medium mb-1">Deal Title*</label>
            <Input id="deal-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Enter deal title" />
          </div>
          <div>
            <label htmlFor="deal-amount" className="block text-sm font-medium mb-1">Amount*</label>
            <Input id="deal-amount" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0.00" type="number" />
          </div>
          <div>
            <label htmlFor="deal-stage" className="block text-sm font-medium mb-1">Stage</label>
            <select 
              id="deal-stage"
              value={stage} 
              onChange={(e) => setStage(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="prospecting">Prospecting</option>
              <option value="qualification">Qualification</option>
              <option value="proposal">Proposal</option>
              <option value="negotiation">Negotiation</option>
              <option value="closed_won">Closed Won</option>
              <option value="closed_lost">Closed Lost</option>
            </select>
          </div>
          {!accountId && (
            <div>
              <label htmlFor="deal-account" className="block text-sm font-medium mb-1">Account</label>
              <select 
                id="deal-account"
                value={selectedAccountId} 
                onChange={(e) => setSelectedAccountId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select an account</option>
                {accounts.map(account => (
                  <option key={account.id} value={account.id}>{account.name}</option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label htmlFor="deal-contact" className="block text-sm font-medium mb-1">Contact</label>
            <select 
              id="deal-contact"
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
            <label htmlFor="deal-close-date" className="block text-sm font-medium mb-1">Close Date</label>
            <Input id="deal-close-date" value={closeDate} onChange={(e) => setCloseDate(e.target.value)} type="date" />
          </div>
        </div>

        <div className="flex justify-end space-x-2 mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>Cancel</Button>
          <Button onClick={handleCreate} disabled={loading}>
            {loading ? "Creating…" : "Create Deal"}
          </Button>
        </div>
      </div>
    </div>
  );
}
