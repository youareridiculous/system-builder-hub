import { getAccounts } from '../lib/api'
import { Card } from '../components/Card'
import { Building2, Mail, Globe } from 'lucide-react'

export default async function AccountsPage() {
  let accounts = []
  try {
    accounts = await getAccounts()
  } catch (error) {
    console.error('Failed to fetch accounts:', error)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Accounts</h1>
        <p className="mt-2 text-gray-600">Manage your company accounts</p>
      </div>

      <div className="grid gap-4">
        {accounts.map((account) => (
          <Card key={account.id} className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Building2 className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    <a href={`/accounts/${account.id}`} className="hover:text-blue-600">
                      {account.name}
                    </a>
                  </h3>
                  <p className="text-sm text-gray-600">{account.industry}</p>
                </div>
              </div>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                {account.website && (
                  <a href={account.website} className="flex items-center space-x-1 hover:text-blue-600">
                    <Globe className="w-4 h-4" />
                    <span>Website</span>
                  </a>
                )}
                <span className="flex items-center space-x-1">
                  <Mail className="w-4 h-4" />
                  <span>Created {new Date(account.created_at).toLocaleDateString()}</span>
                </span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {accounts.length === 0 && (
        <Card className="p-8 text-center">
          <Building2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No accounts found</h3>
          <p className="text-gray-600">Get started by creating your first account.</p>
        </Card>
      )}
    </div>
  )
}
