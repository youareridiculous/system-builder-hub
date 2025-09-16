import * as React from "react";
import { Button } from "../Button";
import { Input } from "../Input";
import { api } from "../../lib/api.ts";
import { useState } from "react";

type Props = { open: boolean; onOpenChange: (v: boolean) => void; onCreated: () => void; };

export function AccountCreateModal({ open, onOpenChange, onCreated }: Props) {
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [website, setWebsite] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function handleCreate() {
    setErr(null);
    if (!name.trim()) { setErr("Company name is required."); return; }
    setLoading(true);
    try {
      await api.post("/accounts/", { name, industry, website });
      onOpenChange(false);
      setName(""); setIndustry(""); setWebsite("");
      onCreated();
    } catch (e: any) {
      setErr(e.message || "Failed to create account.");
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Opaque overlay */}
      <div className="fixed inset-0 bg-black/60 backdrop-blur-[2px]" onClick={() => onOpenChange(false)} />
      
      {/* Modal content */}
      <div className="relative bg-white rounded-xl shadow-2xl p-6 w-full max-w-lg mx-4">
        <div className="mb-4">
          <h2 className="text-xl font-semibold">Create New Account</h2>
          <p className="text-gray-600 text-sm">Add a new company account to your CRM system</p>
        </div>

        {err && <div className="text-red-600 text-sm mb-4 p-2 bg-red-50 rounded">{err}</div>}

        <div className="space-y-4">
          <div>
            <label htmlFor="account-name" className="block text-sm font-medium mb-1">Company Name*</label>
            <Input id="account-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Enter company name" />
          </div>
          <div>
            <label htmlFor="account-industry" className="block text-sm font-medium mb-1">Industry</label>
            <Input id="account-industry" value={industry} onChange={(e) => setIndustry(e.target.value)} placeholder="Enter industry" />
          </div>
          <div>
            <label htmlFor="account-website" className="block text-sm font-medium mb-1">Website</label>
            <Input id="account-website" value={website} onChange={(e) => setWebsite(e.target.value)} placeholder="https://example.com" />
          </div>
        </div>

        <div className="flex justify-end space-x-2 mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>Cancel</Button>
          <Button onClick={handleCreate} disabled={loading}>
            {loading ? "Creating…" : "Create Account"}
          </Button>
        </div>
      </div>
    </div>
  );
}
