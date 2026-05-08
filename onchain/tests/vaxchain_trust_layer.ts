import * as anchor from "@coral-xyz/anchor";
import { web3, BN } from "@coral-xyz/anchor";
import { expect } from "chai";

const { Keypair, PublicKey, SystemProgram } = web3;

type AnchorErrorShape = {
  error?: {
    errorCode?: { code?: string; number?: number };
  };
  logs?: string[];
};

function bytes32(seed: number): number[] {
  return Array.from({ length: 32 }, (_, i) => (seed + i) % 256);
}

function randomHubCode(): string {
  const suffix = Math.random().toString(36).slice(2, 8).toUpperCase();
  return `H${suffix}`;
}

function extractCode(err: unknown): string | undefined {
  const e = err as AnchorErrorShape;
  return e?.error?.errorCode?.code;
}

async function ensureValidatorIsRunning(
  connection: web3.Connection
): Promise<void> {
  const timeoutMs = 3000;

  try {
    await Promise.race([
      connection.getLatestBlockhash("processed"),
      new Promise<never>((_, reject) => {
        setTimeout(
          () => reject(new Error(`RPC probe timed out after ${timeoutMs}ms`)),
          timeoutMs
        );
      }),
    ]);
  } catch (err) {
    const reason = err instanceof Error ? err.message : String(err);
    const rpcUrl = connection.rpcEndpoint;
    throw new Error(
      `Local validator is not reachable at ${rpcUrl}. Start it first with ` +
        `"solana-test-validator --bind-address 127.0.0.1 --rpc-port 8899 --faucet-port 9900". ` +
        `Original error: ${reason}`
    );
  }
}

async function ensureFaucetIsAvailable(
  connection: web3.Connection,
  recipient: web3.PublicKey
): Promise<void> {
  const timeoutMs = 5000;

  try {
    const signature = (await Promise.race([
      connection.requestAirdrop(recipient, 1),
      new Promise<string>((_, reject) => {
        setTimeout(
          () => reject(new Error(`Faucet probe timed out after ${timeoutMs}ms`)),
          timeoutMs
        );
      }),
    ])) as string;

    await Promise.race([
      connection.confirmTransaction(signature, "confirmed"),
      new Promise<void>((_, reject) => {
        setTimeout(
          () =>
            reject(new Error(`Faucet confirmation timed out after ${timeoutMs}ms`)),
          timeoutMs
        );
      }),
    ]);
  } catch (err) {
    const reason = err instanceof Error ? err.message : String(err);
    const rpcUrl = connection.rpcEndpoint;
    throw new Error(
      `Local validator RPC is reachable at ${rpcUrl}, but faucet is not available. ` +
        `Ensure the validator is started with faucet enabled (for example: ` +
        `"solana-test-validator --bind-address 127.0.0.1 --rpc-port 8899 --faucet-port 9900"). ` +
        `Original error: ${reason}`
    );
  }
}

async function expectAnchorError(
  action: () => Promise<unknown>,
  expectedCode: string
): Promise<void> {
  try {
    await action();
    expect.fail(`Expected Anchor error ${expectedCode}`);
  } catch (err) {
    const code = extractCode(err);
    if (code) {
      expect(code).to.equal(expectedCode);
      return;
    }

    const logs = (err as AnchorErrorShape)?.logs?.join(" ") ?? "";
    const text = String(err);
    expect(`${logs} ${text}`).to.include(expectedCode);
  }
}

describe("vaxchain_trust_layer hardening", () => {
  const admin = Keypair.generate();
  const provider = new anchor.AnchorProvider(
    new web3.Connection(
      process.env.ANCHOR_PROVIDER_URL ?? "http://127.0.0.1:8899",
      "confirmed"
    ),
    new anchor.Wallet(admin),
    { commitment: "confirmed" }
  );
  anchor.setProvider(provider);

  const idl = require("../target/idl/vaxchain_trust_layer.json");
  const program: any = new anchor.Program(idl as anchor.Idl, provider);

  const wallet = (provider.wallet as anchor.Wallet).publicKey;
  const configPda = PublicKey.findProgramAddressSync(
    [Buffer.from("config")],
    program.programId
  )[0];

  const outsider = Keypair.generate();
  const rotatedAuthority = Keypair.generate();
  const hubAuthority = Keypair.generate();

  const testHubCode = randomHubCode();
  const hubPda = PublicKey.findProgramAddressSync(
    [Buffer.from("hub"), Buffer.from(testHubCode)],
    program.programId
  )[0];

  before(async () => {
    await ensureValidatorIsRunning(provider.connection);
    await ensureFaucetIsAvailable(provider.connection, admin.publicKey);

    const adminSig = await provider.connection.requestAirdrop(
      admin.publicKey,
      2 * web3.LAMPORTS_PER_SOL
    );
    await provider.connection.confirmTransaction(adminSig, "confirmed");

    const sig = await provider.connection.requestAirdrop(
      outsider.publicKey,
      web3.LAMPORTS_PER_SOL
    );
    await provider.connection.confirmTransaction(sig, "confirmed");

    const existingConfig = await provider.connection.getAccountInfo(configPda);
    if (!existingConfig) {
      await program.methods
        .initializeNetwork(Keypair.generate().publicKey)
        .accounts({
          config: configPda,
          authority: wallet,
          systemProgram: SystemProgram.programId,
        })
        .rpc();
    }
  });

  it("rejects default compression tree", async () => {
    await expectAnchorError(
      async () => {
        await program.methods
          .setCompressionTree(PublicKey.default)
          .accounts({
            config: configPda,
            authority: wallet,
          })
          .rpc();
      },
      "InvalidCompressionTree"
    );
  });

  it("rejects empty hub code", async () => {
    const emptyHubPda = PublicKey.findProgramAddressSync(
      [Buffer.from("hub"), Buffer.from("")],
      program.programId
    )[0];

    await expectAnchorError(
      async () => {
        await program.methods
          .registerHub("", bytes32(7))
          .accounts({
            config: configPda,
            hub: emptyHubPda,
            hubAuthority: hubAuthority.publicKey,
            authority: wallet,
            systemProgram: SystemProgram.programId,
          })
          .rpc();
      },
      "EmptyHubCode"
    );
  });

  it("rejects default hub authority", async () => {
    const code = randomHubCode();
    const pda = PublicKey.findProgramAddressSync(
      [Buffer.from("hub"), Buffer.from(code)],
      program.programId
    )[0];

    await expectAnchorError(
      async () => {
        await program.methods
          .registerHub(code, bytes32(9))
          .accounts({
            config: configPda,
            hub: pda,
            hubAuthority: PublicKey.default,
            authority: wallet,
            systemProgram: SystemProgram.programId,
          })
          .rpc();
      },
      "InvalidAuthorityKey"
    );
  });

  it("rejects unauthorized network authority rotation", async () => {
    await expectAnchorError(
      async () => {
        await program.methods
          .rotateNetworkAuthority(rotatedAuthority.publicKey)
          .accounts({
            config: configPda,
            authority: outsider.publicKey,
          })
          .signers([outsider])
          .rpc();
      },
      "UnauthorizedNetworkAuthority"
    );
  });

  it("rotates network authority and rotates back", async () => {
    await program.methods
      .rotateNetworkAuthority(rotatedAuthority.publicKey)
      .accounts({
        config: configPda,
        authority: wallet,
      })
      .rpc();

    await program.methods
      .rotateNetworkAuthority(wallet)
      .accounts({
        config: configPda,
        authority: rotatedAuthority.publicKey,
      })
      .signers([rotatedAuthority])
      .rpc();
  });

  it("deactivates and reactivates hub with guard checks", async () => {
    await program.methods
      .registerHub(testHubCode, bytes32(11))
      .accounts({
        config: configPda,
        hub: hubPda,
        hubAuthority: hubAuthority.publicKey,
        authority: wallet,
        systemProgram: SystemProgram.programId,
      })
      .rpc();

    await expectAnchorError(
      async () => {
        await program.methods
          .deactivateHub()
          .accounts({
            config: configPda,
            hub: hubPda,
            authority: outsider.publicKey,
          })
          .signers([outsider])
          .rpc();
      },
      "UnauthorizedNetworkAuthority"
    );

    await program.methods
      .deactivateHub()
      .accounts({
        config: configPda,
        hub: hubPda,
        authority: wallet,
      })
      .rpc();

    await expectAnchorError(
      async () => {
        await program.methods
          .deactivateHub()
          .accounts({
            config: configPda,
            hub: hubPda,
            authority: wallet,
          })
          .rpc();
      },
      "HubAlreadyInactive"
    );

    await program.methods
      .reactivateHub()
      .accounts({
        config: configPda,
        hub: hubPda,
        authority: wallet,
      })
      .rpc();

    await expectAnchorError(
      async () => {
        await program.methods
          .reactivateHub()
          .accounts({
            config: configPda,
            hub: hubPda,
            authority: wallet,
          })
          .rpc();
      },
      "HubAlreadyActive"
    );
  });

  it("rejects empty batch code and empty medicine code", async () => {
    const code = randomHubCode();
    const pda = PublicKey.findProgramAddressSync(
      [Buffer.from("hub"), Buffer.from(code)],
      program.programId
    )[0];

    await program.methods
      .registerHub(code, bytes32(13))
      .accounts({
        config: configPda,
        hub: pda,
        hubAuthority: hubAuthority.publicKey,
        authority: wallet,
        systemProgram: SystemProgram.programId,
      })
      .rpc();

    const batchIdHashA = bytes32(21);
    const batchPdaA = PublicKey.findProgramAddressSync(
      [Buffer.from("batch"), Buffer.from(batchIdHashA)],
      program.programId
    )[0];

    const paramsEmptyBatch: Record<string, unknown> = {
      batchIdHash: batchIdHashA,
      batch_id_hash: batchIdHashA,
      batchCode: "",
      batch_code: "",
      medicineCode: "MED-001",
      medicine_code: "MED-001",
      totalUnits: new BN(100),
      total_units: new BN(100),
      documentHash: bytes32(22),
      document_hash: bytes32(22),
      metadataHash: bytes32(23),
      metadata_hash: bytes32(23),
    };

    await expectAnchorError(
      async () => {
        await program.methods
          .createBatch(paramsEmptyBatch)
          .accounts({
            config: configPda,
            hub: pda,
            batch: batchPdaA,
            authority: hubAuthority.publicKey,
            systemProgram: SystemProgram.programId,
          })
          .signers([hubAuthority])
          .rpc();
      },
      "EmptyBatchCode"
    );

    const batchIdHashB = bytes32(24);
    const batchPdaB = PublicKey.findProgramAddressSync(
      [Buffer.from("batch"), Buffer.from(batchIdHashB)],
      program.programId
    )[0];

    const paramsEmptyMedicine: Record<string, unknown> = {
      batchIdHash: batchIdHashB,
      batch_id_hash: batchIdHashB,
      batchCode: "BATCH-001",
      batch_code: "BATCH-001",
      medicineCode: "",
      medicine_code: "",
      totalUnits: new BN(100),
      total_units: new BN(100),
      documentHash: bytes32(25),
      document_hash: bytes32(25),
      metadataHash: bytes32(26),
      metadata_hash: bytes32(26),
    };

    await expectAnchorError(
      async () => {
        await program.methods
          .createBatch(paramsEmptyMedicine)
          .accounts({
            config: configPda,
            hub: pda,
            batch: batchPdaB,
            authority: hubAuthority.publicKey,
            systemProgram: SystemProgram.programId,
          })
          .signers([hubAuthority])
          .rpc();
      },
      "EmptyMedicineCode"
    );
  });
});
