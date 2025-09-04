#!/usr/bin/env node

import { Command } from '@oclif/core';
import { Config } from '@oclif/core/lib/config/config';
import { run } from '@oclif/core';

class SBHCLI extends Command {
  static description = 'SBH Developer Experience CLI';
  static version = '1.0.0';

  async run() {
    const { flags, args } = await this.parse(SBHCLI);
    
    // Show help if no command provided
    if (!args.length) {
      await this._help();
      return;
    }
  }
}

// Run the CLI
run(SBHCLI, process.argv.slice(2)).catch(require('@oclif/core/handle'));
