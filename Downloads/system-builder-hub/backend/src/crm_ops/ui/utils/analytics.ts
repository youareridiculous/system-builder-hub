interface AnalyticsEvent {
  event: string;
  properties?: Record<string, any>;
  userId?: string;
  tenantId?: string;
}

export const trackEvent = (event: string, properties: Record<string, any> = {}) => {
  const userId = localStorage.getItem('user_id');
  const tenantId = localStorage.getItem('tenant_id');

  const analyticsEvent: AnalyticsEvent = {
    event,
    properties: {
      ...properties,
      timestamp: new Date().toISOString(),
    },
    userId,
    tenantId,
  };

  // Send to analytics service
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', event, properties);
  }

  // Log to console in development
  if (process.env.NODE_ENV === 'development') {
    console.log('Analytics Event:', analyticsEvent);
  }

  // Send to backend analytics endpoint
  fetch('/api/analytics/events', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
      'X-Tenant-Slug': localStorage.getItem('tenant_slug') || '',
    },
    body: JSON.stringify(analyticsEvent),
  }).catch(console.error);
};

// Predefined analytics events
export const AnalyticsEvents = {
  // Contact events
  CONTACT_CREATED: 'ui.contact.created',
  CONTACT_UPDATED: 'ui.contact.updated',
  CONTACT_DELETED: 'ui.contact.deleted',
  CONTACT_VIEWED: 'ui.contact.viewed',

  // Deal events
  DEAL_CREATED: 'ui.deal.created',
  DEAL_UPDATED: 'ui.deal.updated',
  DEAL_DELETED: 'ui.deal.deleted',
  DEAL_STAGE_CHANGED: 'ui.deal.stage_changed',
  DEAL_STATUS_CHANGED: 'ui.deal.status_changed',

  // Activity events
  ACTIVITY_CREATED: 'ui.activity.created',
  ACTIVITY_COMPLETED: 'ui.activity.completed',
  ACTIVITY_VIEWED: 'ui.activity.viewed',

  // Project events
  PROJECT_CREATED: 'ui.project.created',
  PROJECT_ARCHIVED: 'ui.project.archived',
  PROJECT_VIEWED: 'ui.project.viewed',

  // Task events
  TASK_CREATED: 'ui.task.created',
  TASK_STATUS_CHANGED: 'ui.task.status_changed',
  TASK_COMPLETED: 'ui.task.completed',

  // Message events
  MESSAGE_SENT: 'ui.message.sent',
  THREAD_CREATED: 'ui.thread.created',

  // Dashboard events
  DASHBOARD_VIEWED: 'ui.dashboard.viewed',
  ANALYTICS_VIEWED: 'ui.analytics.viewed',

  // Admin events
  SUBSCRIPTION_UPDATED: 'ui.subscription.updated',
  USER_ROLE_CHANGED: 'ui.user.role_changed',
} as const;
