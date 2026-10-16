import { expect, test } from '@playwright/test'

const mailpitUrl = process.env.PLAYWRIGHT_MAILPIT_URL ?? 'http://127.0.0.1:8025'

interface MailpitMessage {
  ID: string
}

interface MailpitMessageList {
  messages: MailpitMessage[]
}

interface MailpitMessageDetail {
  Text?: string
  HTML?: string
}

async function clearMailbox() {
  const response = await fetch(`${mailpitUrl}/api/v1/messages`, { method: 'DELETE' })
  if (!response.ok) {
    throw new Error(`Unable to clear Mailpit: HTTP ${response.status}`)
  }
}

async function waitForOtp(): Promise<string> {
  const deadline = Date.now() + 20_000
  while (Date.now() < deadline) {
    const response = await fetch(`${mailpitUrl}/api/v1/messages`)
    if (!response.ok) {
      throw new Error(`Unable to read Mailpit: HTTP ${response.status}`)
    }
    const { messages } = (await response.json()) as MailpitMessageList
    for (const message of messages) {
      const detailResponse = await fetch(
        `${mailpitUrl}/api/v1/message/${encodeURIComponent(message.ID)}`,
      )
      if (!detailResponse.ok) {
        throw new Error(`Unable to read Mailpit message: HTTP ${detailResponse.status}`)
      }
      const detail = (await detailResponse.json()) as MailpitMessageDetail
      const code = `${detail.Text ?? ''}\n${detail.HTML ?? ''}`.match(/code is:\s*(\d{6})/i)?.[1]
      if (code) return code
    }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error('No six-digit OTP arrived in Mailpit within 20 seconds')
}

test('completes the real email OTP login flow', async ({ page }) => {
  test.setTimeout(30_000)
  const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD
  if (!password) {
    throw new Error('PLAYWRIGHT_ADMIN_PASSWORD must be set for the end-to-end login test')
  }

  await clearMailbox()
  await page.goto('/')
  await page.getByLabel('Username').fill('admin')
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.getByRole('heading', { name: 'Enter your OTP' })).toBeVisible()

  await page.getByLabel('6-digit code').fill(await waitForOtp())
  await page.getByRole('button', { name: 'Verify' }).click()
  await expect(page.getByText('admin · master')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Payslip' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Bills' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Inventory' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Employees' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Company' })).toBeDisabled()
})
