import React from "react";
import { Input } from "../Input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../Select";
import { Button } from "../Button";
import { Filter, Search } from "lucide-react";

export function WebhooksFilters({ filters, onFilterChange, onClearFilters }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
      <div>
        <label className="text-sm font-medium">Provider</label>
        <Select value={filters.provider} onValueChange={(value) => onFilterChange("provider", value)}>
          <SelectTrigger>
            <SelectValue placeholder="All providers" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All providers</SelectItem>
            <SelectItem value="sendgrid">SendGrid</SelectItem>
            <SelectItem value="twilio">Twilio</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      <div>
        <label className="text-sm font-medium">Search</label>
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
          <Input 
            placeholder="Search events..." 
            value={filters.search} 
            onChange={(e) => onFilterChange("search", e.target.value)} 
            className="pl-10" 
          />
        </div>
      </div>
      
      <div className="flex items-end">
        <Button variant="outline" onClick={onClearFilters}>
          <Filter className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}
