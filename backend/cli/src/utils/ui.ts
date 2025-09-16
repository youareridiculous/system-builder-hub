import chalk from 'chalk';
import ora from 'ora';
import inquirer from 'inquirer';

export class UI {
  static spinner: ora.Ora | null = null;

  static startSpinner(text: string): ora.Ora {
    this.spinner = ora(text).start();
    return this.spinner;
  }

  static stopSpinner(success = true, text?: string): void {
    if (this.spinner) {
      if (success) {
        this.spinner.succeed(text);
      } else {
        this.spinner.fail(text);
      }
      this.spinner = null;
    }
  }

  static success(message: string): void {
    console.log(chalk.green(`✅ ${message}`));
  }

  static error(message: string): void {
    console.error(chalk.red(`❌ ${message}`));
  }

  static warning(message: string): void {
    console.log(chalk.yellow(`⚠️  ${message}`));
  }

  static info(message: string): void {
    console.log(chalk.blue(`ℹ️  ${message}`));
  }

  static log(message: string): void {
    console.log(message);
  }

  static async prompt(questions: any[]): Promise<any> {
    return inquirer.prompt(questions);
  }

  static async confirm(message: string, defaultAnswer = false): Promise<boolean> {
    const { confirmed } = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'confirmed',
        message,
        default: defaultAnswer,
      },
    ]);
    return confirmed;
  }

  static async select(message: string, choices: string[]): Promise<string> {
    const { selected } = await inquirer.prompt([
      {
        type: 'list',
        name: 'selected',
        message,
        choices,
      },
    ]);
    return selected;
  }

  static async input(message: string, defaultAnswer?: string): Promise<string> {
    const { value } = await inquirer.prompt([
      {
        type: 'input',
        name: 'value',
        message,
        default: defaultAnswer,
      },
    ]);
    return value;
  }

  static async password(message: string): Promise<string> {
    const { value } = await inquirer.prompt([
      {
        type: 'password',
        name: 'value',
        message,
      },
    ]);
    return value;
  }

  static table(data: any[]): void {
    if (data.length === 0) {
      console.log(chalk.gray('No data to display'));
      return;
    }

    const headers = Object.keys(data[0]);
    const maxWidths = headers.map(header => {
      const maxLength = Math.max(
        header.length,
        ...data.map(row => String(row[header] || '').length)
      );
      return Math.min(maxLength, 50);
    });

    // Print headers
    const headerRow = headers.map((header, i) => 
      chalk.bold(header.padEnd(maxWidths[i]))
    ).join(' | ');
    console.log(headerRow);
    console.log('-'.repeat(headerRow.length));

    // Print data rows
    data.forEach(row => {
      const dataRow = headers.map((header, i) => {
        const value = String(row[header] || '');
        return value.length > maxWidths[i] 
          ? value.substring(0, maxWidths[i] - 3) + '...'
          : value.padEnd(maxWidths[i]);
      }).join(' | ');
      console.log(dataRow);
    });
  }

  static progressBar(current: number, total: number, width = 40): void {
    const percentage = Math.round((current / total) * 100);
    const filled = Math.round((width * current) / total);
    const empty = width - filled;
    
    const filledBar = chalk.green('█'.repeat(filled));
    const emptyBar = chalk.gray('░'.repeat(empty));
    
    process.stdout.write(`\r[${filledBar}${emptyBar}] ${percentage}%`);
    
    if (current === total) {
      process.stdout.write('\n');
    }
  }
}
