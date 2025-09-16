import { getContacts, getAccounts } from '../lib/api'
import { Card } from '../components/Card'
import { User, Mail, Phone, Building2 } from 'lucide-react'

export default async function ContactsPage() {
  let contacts = []
  let accounts = []
  
  try {
    [contacts, accounts] = await Promise.all([getContacts(), getAccounts()])
  } catch (error) {
    console.error('Failed to fetch contacts:', error)
  }

  // Create accounts lookup
  const accountsMap = new Map(accounts.map(acc => [acc.id, acc]))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Contacts</h1>
        <p className="mt-2 text-gray-600">Manage your contact information</p>
      </div>

      <div className="grid gap-4">
        {contacts.map((contact) => {
          const account = accountsMap.get(contact.account_id)
          return (
            <Card key={contact.id} className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                    <User className="w-5 h-5 text-green-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">
                      <a href={`/contacts/${contact.id}`} className="hover:text-blue-600">
                        {contact.first_name} {contact.last_name}
                      </a>
                    </h3>
                    <p className="text-sm text-gray-600">{contact.email}</p>
                    {account && (
                      <p className="text-sm text-gray-500">
                        {account.name}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-4 text-sm text-gray-500">
                  {contact.phone && (
                    <span className="flex items-center space-x-1">
                      <Phone className="w-4 h-4" />
                      <span>{contact.phone}</span>
                    </span>
                  )}
                  <span className="flex items-center space-x-1">
                    <Mail className="w-4 h-4" />
                    <span>{contact.email}</span>
                  </span>
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {contacts.length === 0 && (
        <Card className="p-8 text-center">
          <User className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No contacts found</h3>
          <p className="text-gray-600">Get started by creating your first contact.</p>
        </Card>
      )}
    </div>
  )
}
