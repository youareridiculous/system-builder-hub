import { getActivities } from '../lib/api'
import { Card } from '../components/Card'
import { Calendar, Clock, User } from 'lucide-react'

export default async function ActivitiesPage() {
  let activities = []
  
  try {
    activities = await getActivities()
  } catch (error) {
    console.error('Failed to fetch activities:', error)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Activities</h1>
        <p className="mt-2 text-gray-600">View recent activities and tasks</p>
      </div>

      <div className="grid gap-4">
        {activities.map((activity) => (
          <Card key={activity.id} className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">{activity.title}</h3>
                  <p className="text-sm text-gray-600">{activity.description}</p>
                  <p className="text-sm text-gray-500">Type: {activity.type}</p>
                </div>
              </div>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <div className="flex items-center space-x-1">
                  <Clock className="w-4 h-4" />
                  <span>{new Date(activity.created_at).toLocaleDateString()}</span>
                </div>
                {activity.assigned_to && (
                  <div className="flex items-center space-x-1">
                    <User className="w-4 h-4" />
                    <span>{activity.assigned_to}</span>
                  </div>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {activities.length === 0 && (
        <Card className="p-8 text-center">
          <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No activities found</h3>
          <p className="text-gray-600">Get started by creating your first activity.</p>
        </Card>
      )}
    </div>
  )
}
