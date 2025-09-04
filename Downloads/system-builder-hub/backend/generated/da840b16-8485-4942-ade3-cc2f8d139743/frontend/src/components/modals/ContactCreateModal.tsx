import * as React from "react";
import { Button } from "../Button";
import { Input } from "../Input";
import { Select } from "../Select";
import { api } from '../../lib/api.ts';
import { useState, useEffect } from "react";

type Props = { open: boolean; onOpenChange: (v: boolean) => void; onCreated: () => void; };

export function ContactCreateModal({ open, onOpenChange, onCreated }: Props) {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [title, setTitle] = useState("");
  const [accountId, setAccountId] = useState("");
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      api.get("/accounts/").then(setAccounts).catch(console.error);
    }
  }, [open]);

  async function handleCreate() {
    setErr(null);
    if (!firstName.trim() || !lastName.trim()) { 
      setErr("First name and last name are required."); 
      return; 
    }
    setLoading(true);
    try {
      await api.post("/contacts/", { 
        first_name: firstName, 
        last_name: lastName, 
        email, 
        phone, 
        title, 
        account_id: accountId || null 
      });
      onOpenChange(false);
      setFirstName(""); setLastName(""); setEmail(""); setPhone(""); setTitle(""); setAccountId("");
      onCreated();
    } catch (e: any) {
      setErr(e.message || "Failed to create contact.");
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
          <h2 className="text-xl font-semibold">Create New Contact</h2>
          <p className="text-gray-600 text-sm">Add a new contact to your CRM system</p>
        </div>

        {err && <div className="text-red-600 text-sm mb-4 p-2 bg-red-50 rounded">{err}</div>}

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">First Name*</label>
              <Input value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="First name" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Last Name*</label>
              <Input value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder="Last name" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email@example.com" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Phone</label>
            <Input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+1 (555) 123-4567" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Title</label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Job title" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Account</label>
            <select 
              value={accountId} 
              onChange={(e) => setAccountId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select an account</option>
              {accounts.map(account => (
                <option key={account.id} value={account.id}>{account.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex justify-end space-x-2 mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>Cancel</Button>
          <Button onClick={handleCreate} disabled={loading}>
            {loading ? "Creating…" : "Create Contact"}
          </Button>
        </div>
      </div>
    </div>
  );
}
