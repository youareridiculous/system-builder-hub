import { getAccounts } from '../../lib/api'
import { Card } from '../../components/Card'
import { Building2, Mail, Globe, Calendar } from 'lucide-react'

export default async function AccountDetailPage({ params }: { params: { id: string } }) {
  let accounts = []
  let account = null
  
  try {
    accounts = await getAccounts()
    account = accounts.find(a => a.id.toString() === params.id)
  } catch (error) {
    console.error('Failed to fetch account:', error)
  }

  if (!account) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Account Not Found</h1>
          <p className="mt-2 text-gray-600">The requested account could not be found.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <a href="/accounts" className="text-blue-600 hover:text-blue-800 mb-4 inline-block">
          ← Back to Accounts
        </a>
        <h1 className="text-3xl font-bold text-gray-900">{account.name}</h1>
        <p className="mt-2 text-gray-600">Account details and information</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Account Information</h2>
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <Building2 className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900">Industry</p>
                <p className="text-sm text-gray-600">{account.industry}</p>
              </div>
            </div>
            {account.website && (
              <div className="flex items-center space-x-3">
                <Globe className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Website</p>
                  <a href={account.website} className="text-sm text-blue-600 hover:text-blue-800">
                    {account.website}
                  </a>
                </div>
              </div>
            )}
            <div className="flex items-center space-x-3">
              <Calendar className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900">Created</p>
                <p className="text-sm text-gray-600">
                  {new Date(account.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <a href="/contacts" className="block w-full text-left p-3 rounded-lg border hover:bg-gray-50 transition-colors">
              <div className="flex items-center space-x-3">
                <Mail className="w-5 h-5 text-blue-600" />
                <span className="text-sm font-medium text-gray-900">View Contacts</span>
              </div>
            </a>
            <a href="/deals" className="block w-full text-left p-3 rounded-lg border hover:bg-gray-50 transition-colors">
              <div className="flex items-center space-x-3">
                <Building2 className="w-5 h-5 text-green-600" />
                <span className="text-sm font-medium text-gray-900">View Deals</span>
              </div>
            </a>
          </div>
        </Card>
      </div>
    </div>
  )
}
