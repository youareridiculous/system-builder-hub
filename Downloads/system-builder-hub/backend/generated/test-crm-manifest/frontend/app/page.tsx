import { getHealth } from './lib/api'
import { Card } from './components/Card'
import { Activity, Users, Building2, Target, Calendar } from 'lucide-react'

export default async function DashboardPage() {
  let health = null
  try {
    health = await getHealth()
  } catch (error) {
    console.error('Health check failed:', error)
  }

  const quickLinks = [
    {
      title: 'Accounts',
      description: 'Manage company accounts',
      href: '/accounts',
      icon: Building2,
      count: 'View all'
    },
    {
      title: 'Contacts',
      description: 'Manage contact information',
      href: '/contacts',
      icon: Users,
      count: 'View all'
    },
    {
      title: 'Deals',
      description: 'Track sales opportunities',
      href: '/deals',
      icon: Target,
      count: 'View all'
    },
    {
      title: 'Activities',
      description: 'View recent activities',
      href: '/activities',
      icon: Calendar,
      count: 'View all'
    }
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">Welcome to your CRM dashboard</p>
      </div>

      {/* Health Status */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">System Status</h2>
            <p className="text-sm text-gray-600">Backend API health</p>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${health?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm font-medium">
              {health?.status === 'healthy' ? 'Healthy' : 'Unreachable'}
            </span>
          </div>
        </div>
      </Card>

      {/* Quick Links */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Links</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickLinks.map((link) => (
            <Card key={link.href} className="hover:shadow-md transition-shadow">
              <a href={link.href} className="block">
                <div className="flex items-center space-x-3">
                  <link.icon className="w-6 h-6 text-blue-600" />
                  <div>
                    <h3 className="font-medium text-gray-900">{link.title}</h3>
                    <p className="text-sm text-gray-600">{link.description}</p>
                  </div>
                </div>
                <div className="mt-3 text-sm text-blue-600">{link.count} →</div>
              </a>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
