import React, { useState } from 'react';
import { Calendar, ChevronDown } from 'lucide-react';
import { Button } from './Button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './Select';
import { Input } from './Input';
import { Label } from './Label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './Dialog';

export interface DateRange {
  from: Date;
  to: Date;
}

interface DateRangePickerProps {
  value: DateRange;
  onValueChange: (range: DateRange) => void;
  className?: string;
}

const presets = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 },
  { label: 'Last 90 days', days: 90 },
  { label: 'Last 6 months', days: 180 },
  { label: 'Last year', days: 365 },
];

export function DateRangePicker({ value, onValueChange, className }: DateRangePickerProps) {
  const [isCustomOpen, setIsCustomOpen] = useState(false);
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');

  const handlePresetSelect = (days: number) => {
    const to = new Date();
    const from = new Date();
    from.setDate(from.getDate() - days);
    onValueChange({ from, to });
  };

  const handleCustomSubmit = () => {
    if (customFrom && customTo) {
      const from = new Date(customFrom);
      const to = new Date(customTo);
      if (!isNaN(from.getTime()) && !isNaN(to.getTime())) {
        onValueChange({ from, to });
        setIsCustomOpen(false);
      }
    }
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: 'numeric'
    });
  };

  const formatDateRange = (range: DateRange) => {
    if (!range.from || !range.to) return 'Select date range';
    
    const fromStr = formatDate(range.from);
    const toStr = formatDate(range.to);
    
    if (range.from.getFullYear() === range.to.getFullYear()) {
      return `${range.from.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${toStr}`;
    }
    return `${fromStr} - ${toStr}`;
  };

  const getCurrentPreset = () => {
    const daysDiff = Math.ceil((value.to.getTime() - value.from.getTime()) / (1000 * 60 * 60 * 24));
    const preset = presets.find(p => p.days === daysDiff);
    return preset ? preset.label : 'custom';
  };

  const getDisplayValue = () => {
    const daysDiff = Math.ceil((value.to.getTime() - value.from.getTime()) / (1000 * 60 * 60 * 24));
    const preset = presets.find(p => p.days === daysDiff);
    return preset ? preset.label : formatDateRange(value);
  };

  const formatDateForInput = (date: Date) => {
    return date.toISOString().split('T')[0];
  };

  return (
    <div className={className}>
      <Select value={getCurrentPreset()} onValueChange={(selected) => {
        if (selected === 'custom') {
          setIsCustomOpen(true);
          setCustomFrom(formatDateForInput(value.from));
          setCustomTo(formatDateForInput(value.to));
        } else {
          const preset = presets.find(p => p.label === selected);
          if (preset) {
            handlePresetSelect(preset.days);
          }
        }
      }}>
        <SelectTrigger className="min-w-48 max-w-80">
          <Calendar className="mr-2 h-4 w-4 flex-shrink-0" />
          <span className="truncate">{getDisplayValue()}</span>
          <ChevronDown className="ml-2 h-4 w-4 flex-shrink-0" />
        </SelectTrigger>
        <SelectContent>
          {presets.map((preset) => (
            <SelectItem key={preset.days} value={preset.label}>
              {preset.label}
            </SelectItem>
          ))}
          <SelectItem value="custom">Custom Range</SelectItem>
        </SelectContent>
      </Select>

      <Dialog open={isCustomOpen} onOpenChange={setIsCustomOpen}>
        <DialogTrigger asChild>
          <div style={{ display: 'none' }} />
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Select Custom Date Range</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="from-date">From Date</Label>
              <Input
                id="from-date"
                type="date"
                value={customFrom}
                onChange={(e) => setCustomFrom(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="to-date">To Date</Label>
              <Input
                id="to-date"
                type="date"
                value={customTo}
                onChange={(e) => setCustomTo(e.target.value)}
              />
            </div>
            <div className="flex justify-end space-x-2">
              <Button variant="outline" onClick={() => setIsCustomOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCustomSubmit}>
                Apply
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
