import { getContacts, getAccounts } from '../../lib/api'
import { Card } from '../../components/Card'
import { User, Mail, Phone, Building2, Calendar } from 'lucide-react'

export default async function ContactDetailPage({ params }: { params: { id: string } }) {
  let contacts = []
  let accounts = []
  let contact = null
  
  try {
    [contacts, accounts] = await Promise.all([getContacts(), getAccounts()])
    contact = contacts.find(c => c.id.toString() === params.id)
  } catch (error) {
    console.error('Failed to fetch contact:', error)
  }

  if (!contact) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Contact Not Found</h1>
          <p className="mt-2 text-gray-600">The requested contact could not be found.</p>
        </div>
      </div>
    )
  }

  const account = accounts.find(a => a.id === contact.account_id)

  return (
    <div className="space-y-6">
      <div>
        <a href="/contacts" className="text-blue-600 hover:text-blue-800 mb-4 inline-block">
          ← Back to Contacts
        </a>
        <h1 className="text-3xl font-bold text-gray-900">
          {contact.first_name} {contact.last_name}
        </h1>
        <p className="mt-2 text-gray-600">Contact details and information</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Contact Information</h2>
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <Mail className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900">Email</p>
                <a href={`mailto:${contact.email}`} className="text-sm text-blue-600 hover:text-blue-800">
                  {contact.email}
                </a>
              </div>
            </div>
            {contact.phone && (
              <div className="flex items-center space-x-3">
                <Phone className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Phone</p>
                  <a href={`tel:${contact.phone}`} className="text-sm text-blue-600 hover:text-blue-800">
                    {contact.phone}
                  </a>
                </div>
              </div>
            )}
            {account && (
              <div className="flex items-center space-x-3">
                <Building2 className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Account</p>
                  <a href={`/accounts/${account.id}`} className="text-sm text-blue-600 hover:text-blue-800">
                    {account.name}
                  </a>
                </div>
              </div>
            )}
            <div className="flex items-center space-x-3">
              <Calendar className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900">Created</p>
                <p className="text-sm text-gray-600">
                  {new Date(contact.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <a href="/deals" className="block w-full text-left p-3 rounded-lg border hover:bg-gray-50 transition-colors">
              <div className="flex items-center space-x-3">
                <Building2 className="w-5 h-5 text-green-600" />
                <span className="text-sm font-medium text-gray-900">View Deals</span>
              </div>
            </a>
            <a href="/activities" className="block w-full text-left p-3 rounded-lg border hover:bg-gray-50 transition-colors">
              <div className="flex items-center space-x-3">
                <Calendar className="w-5 h-5 text-blue-600" />
                <span className="text-sm font-medium text-gray-900">View Activities</span>
              </div>
            </a>
          </div>
        </Card>
      </div>
    </div>
  )
}
