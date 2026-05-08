use anchor_lang::prelude::*;

declare_id!("8had5koATJfLWrZ5yMrnSsQ5Ssc5aW4EWNtwrHzb4Prz");

const HUB_CODE_MAX_LEN: usize = 16;
const BATCH_CODE_MAX_LEN: usize = 64;
const MEDICINE_CODE_MAX_LEN: usize = 32;

const STATUS_CREATED: u8 = 0;
const STATUS_IN_TRANSIT: u8 = 1;
const STATUS_RECEIVED: u8 = 2;
const STATUS_DISPENSED: u8 = 3;

const TRANSFER_INITIATED: u8 = 0;
const TRANSFER_RECEIVED: u8 = 1;

#[program]
pub mod vaxchain_trust_layer {
    use super::*;

    pub fn initialize_network(
        ctx: Context<InitializeNetwork>,
        compression_tree: Pubkey,
    ) -> Result<()> {
        assert_valid_compression_tree(compression_tree)?;

        let config = &mut ctx.accounts.config;
        config.authority = ctx.accounts.authority.key();
        config.compression_tree = compression_tree;
        config.version = 1;
        config.hub_count = 0;
        config.batch_count = 0;
        config.bump = ctx.bumps.config;

        emit!(NetworkInitialized {
            authority: config.authority,
            compression_tree,
        });

        Ok(())
    }

    pub fn set_compression_tree(
        ctx: Context<SetCompressionTree>,
        compression_tree: Pubkey,
    ) -> Result<()> {
        assert_valid_compression_tree(compression_tree)?;

        let config = &mut ctx.accounts.config;
        config.compression_tree = compression_tree;

        emit!(CompressionTreeUpdated {
            authority: ctx.accounts.authority.key(),
            compression_tree,
        });

        Ok(())
    }

    pub fn rotate_network_authority(
        ctx: Context<RotateNetworkAuthority>,
        new_authority: Pubkey,
    ) -> Result<()> {
        require!(
            new_authority != Pubkey::default(),
            VaxchainError::InvalidAuthorityKey
        );

        let config = &mut ctx.accounts.config;
        let previous_authority = config.authority;
        config.authority = new_authority;

        emit!(NetworkAuthorityRotated {
            previous_authority,
            new_authority,
        });

        Ok(())
    }

    pub fn register_hub(
        ctx: Context<RegisterHub>,
        hub_code: String,
        hub_label_hash: [u8; 32],
    ) -> Result<()> {
        require!(!hub_code.as_bytes().is_empty(), VaxchainError::EmptyHubCode);
        require!(hub_code.as_bytes().len() <= HUB_CODE_MAX_LEN, VaxchainError::HubCodeTooLong);
        require!(
            ctx.accounts.hub_authority.key() != Pubkey::default(),
            VaxchainError::InvalidAuthorityKey
        );

        let config = &mut ctx.accounts.config;
        let hub = &mut ctx.accounts.hub;

        hub.authority = ctx.accounts.hub_authority.key();
        hub.hub_code = hub_code.clone();
        hub.hub_label_hash = hub_label_hash;
        hub.is_active = true;
        hub.bump = ctx.bumps.hub;

        config.hub_count = config
            .hub_count
            .checked_add(1)
            .ok_or(VaxchainError::MathOverflow)?;

        emit!(HubRegistered {
            hub: hub.key(),
            authority: hub.authority,
            hub_code,
        });

        Ok(())
    }

    pub fn deactivate_hub(ctx: Context<ManageHubStatus>) -> Result<()> {
        let hub = &mut ctx.accounts.hub;
        require!(hub.is_active, VaxchainError::HubAlreadyInactive);

        hub.is_active = false;

        emit!(HubDeactivated {
            hub: hub.key(),
            authority: ctx.accounts.authority.key(),
            hub_code: hub.hub_code.clone(),
        });

        Ok(())
    }

    pub fn reactivate_hub(ctx: Context<ManageHubStatus>) -> Result<()> {
        let hub = &mut ctx.accounts.hub;
        require!(!hub.is_active, VaxchainError::HubAlreadyActive);

        hub.is_active = true;

        emit!(HubReactivated {
            hub: hub.key(),
            authority: ctx.accounts.authority.key(),
            hub_code: hub.hub_code.clone(),
        });

        Ok(())
    }

    pub fn create_batch(ctx: Context<CreateBatch>, params: CreateBatchParams) -> Result<()> {
        params.validate()?;
        assert_hub_authority(&ctx.accounts.hub, &ctx.accounts.authority)?;

        let config = &mut ctx.accounts.config;
        let batch = &mut ctx.accounts.batch;
        let now = Clock::get()?.unix_timestamp;

        batch.batch_id_hash = params.batch_id_hash;
        batch.batch_code = params.batch_code.clone();
        batch.medicine_code = params.medicine_code.clone();
        batch.document_hash = params.document_hash;
        batch.metadata_hash = params.metadata_hash;
        batch.current_hub = ctx.accounts.hub.key();
        batch.created_by = ctx.accounts.authority.key();
        batch.total_units = params.total_units;
        batch.remaining_units = params.total_units;
        batch.dispensed_units = 0;
        batch.transfer_nonce = 0;
        batch.status = STATUS_CREATED;
        batch.created_at = now;
        batch.updated_at = now;
        batch.bump = ctx.bumps.batch;

        config.batch_count = config
            .batch_count
            .checked_add(1)
            .ok_or(VaxchainError::MathOverflow)?;

        emit!(BatchCreated {
            batch: batch.key(),
            batch_id_hash: batch.batch_id_hash,
            current_hub: batch.current_hub,
            total_units: batch.total_units,
            document_hash: batch.document_hash,
        });

        Ok(())
    }

    pub fn record_intake(
        ctx: Context<RecordIntake>,
        intake_reference_hash: [u8; 32],
    ) -> Result<()> {
        assert_hub_authority(&ctx.accounts.hub, &ctx.accounts.authority)?;

        let batch = &mut ctx.accounts.batch;
        require_keys_eq!(batch.current_hub, ctx.accounts.hub.key(), VaxchainError::InvalidCurrentHub);
        require!(batch.status == STATUS_CREATED, VaxchainError::InvalidBatchState);

        batch.status = STATUS_RECEIVED;
        batch.updated_at = Clock::get()?.unix_timestamp;

        emit!(IntakeRecorded {
            batch: batch.key(),
            hub: ctx.accounts.hub.key(),
            reference_hash: intake_reference_hash,
        });

        Ok(())
    }

    pub fn initiate_transfer(
        ctx: Context<InitiateTransfer>,
        reference_hash: [u8; 32],
    ) -> Result<()> {
        assert_hub_authority(&ctx.accounts.source_hub, &ctx.accounts.authority)?;
        require!(ctx.accounts.destination_hub.is_active, VaxchainError::HubInactive);
        require!(
            ctx.accounts.source_hub.key() != ctx.accounts.destination_hub.key(),
            VaxchainError::DestinationHubMustDiffer
        );

        let batch = &mut ctx.accounts.batch;
        require_keys_eq!(batch.current_hub, ctx.accounts.source_hub.key(), VaxchainError::InvalidCurrentHub);
        require!(batch.status == STATUS_RECEIVED, VaxchainError::InvalidBatchState);
        require!(batch.remaining_units > 0, VaxchainError::NothingToTransfer);

        let transfer = &mut ctx.accounts.transfer;
        let now = Clock::get()?.unix_timestamp;

        transfer.batch = batch.key();
        transfer.batch_id_hash = batch.batch_id_hash;
        transfer.from_hub = ctx.accounts.source_hub.key();
        transfer.to_hub = ctx.accounts.destination_hub.key();
        transfer.quantity = batch.remaining_units;
        transfer.status = TRANSFER_INITIATED;
        transfer.reference_hash = reference_hash;
        transfer.initiated_by = ctx.accounts.authority.key();
        transfer.received_by = Pubkey::default();
        transfer.initiated_at = now;
        transfer.received_at = 0;
        transfer.nonce = batch.transfer_nonce;
        transfer.bump = ctx.bumps.transfer;

        batch.status = STATUS_IN_TRANSIT;
        batch.transfer_nonce = batch
            .transfer_nonce
            .checked_add(1)
            .ok_or(VaxchainError::MathOverflow)?;
        batch.updated_at = now;

        emit!(TransferInitiated {
            transfer: transfer.key(),
            batch: batch.key(),
            from_hub: transfer.from_hub,
            to_hub: transfer.to_hub,
            quantity: transfer.quantity,
            nonce: transfer.nonce,
        });

        Ok(())
    }

    pub fn receive_transfer(ctx: Context<ReceiveTransfer>) -> Result<()> {
        assert_hub_authority(&ctx.accounts.destination_hub, &ctx.accounts.authority)?;

        let batch = &mut ctx.accounts.batch;
        let transfer = &mut ctx.accounts.transfer;
        let now = Clock::get()?.unix_timestamp;

        require_keys_eq!(transfer.batch, batch.key(), VaxchainError::TransferBatchMismatch);
        require_keys_eq!(transfer.to_hub, ctx.accounts.destination_hub.key(), VaxchainError::WrongDestinationHub);
        require!(transfer.status == TRANSFER_INITIATED, VaxchainError::TransferAlreadySettled);
        require!(batch.status == STATUS_IN_TRANSIT, VaxchainError::InvalidBatchState);

        transfer.status = TRANSFER_RECEIVED;
        transfer.received_by = ctx.accounts.authority.key();
        transfer.received_at = now;

        batch.current_hub = ctx.accounts.destination_hub.key();
        batch.status = STATUS_RECEIVED;
        batch.updated_at = now;

        emit!(TransferReceived {
            transfer: transfer.key(),
            batch: batch.key(),
            destination_hub: batch.current_hub,
            quantity: transfer.quantity,
            nonce: transfer.nonce,
        });

        Ok(())
    }

    pub fn record_dispensation(
        ctx: Context<RecordDispensation>,
        quantity: u64,
        reference_hash: [u8; 32],
    ) -> Result<()> {
        require!(quantity > 0, VaxchainError::InvalidQuantity);
        assert_hub_authority(&ctx.accounts.hub, &ctx.accounts.authority)?;

        let batch = &mut ctx.accounts.batch;
        require_keys_eq!(batch.current_hub, ctx.accounts.hub.key(), VaxchainError::InvalidCurrentHub);
        require!(batch.status == STATUS_RECEIVED, VaxchainError::InvalidBatchState);
        require!(batch.remaining_units >= quantity, VaxchainError::InsufficientUnits);

        batch.remaining_units = batch
            .remaining_units
            .checked_sub(quantity)
            .ok_or(VaxchainError::MathOverflow)?;
        batch.dispensed_units = batch
            .dispensed_units
            .checked_add(quantity)
            .ok_or(VaxchainError::MathOverflow)?;
        batch.status = if batch.remaining_units == 0 {
            STATUS_DISPENSED
        } else {
            STATUS_RECEIVED
        };
        batch.updated_at = Clock::get()?.unix_timestamp;

        emit!(DispensationRecorded {
            batch: batch.key(),
            hub: ctx.accounts.hub.key(),
            dispensed_units: quantity,
            remaining_units: batch.remaining_units,
            reference_hash,
        });

        Ok(())
    }
}

fn assert_hub_authority<'info>(
    hub: &Account<'info, HubAccount>,
    authority: &Signer<'info>,
) -> Result<()> {
    require!(hub.is_active, VaxchainError::HubInactive);
    require_keys_eq!(hub.authority, authority.key(), VaxchainError::UnauthorizedHubAuthority);
    Ok(())
}

fn assert_valid_compression_tree(compression_tree: Pubkey) -> Result<()> {
    require!(
        compression_tree != Pubkey::default(),
        VaxchainError::InvalidCompressionTree
    );
    Ok(())
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone)]
pub struct CreateBatchParams {
    pub batch_id_hash: [u8; 32],
    pub batch_code: String,
    pub medicine_code: String,
    pub total_units: u64,
    pub document_hash: [u8; 32],
    pub metadata_hash: [u8; 32],
}

impl CreateBatchParams {
    fn validate(&self) -> Result<()> {
        require!(!self.batch_code.as_bytes().is_empty(), VaxchainError::EmptyBatchCode);
        require!(
            !self.medicine_code.as_bytes().is_empty(),
            VaxchainError::EmptyMedicineCode
        );
        require!(
            self.batch_code.as_bytes().len() <= BATCH_CODE_MAX_LEN,
            VaxchainError::BatchCodeTooLong
        );
        require!(
            self.medicine_code.as_bytes().len() <= MEDICINE_CODE_MAX_LEN,
            VaxchainError::MedicineCodeTooLong
        );
        require!(self.total_units > 0, VaxchainError::InvalidQuantity);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct InitializeNetwork<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + NetworkConfig::MAX_SIZE,
        seeds = [b"config"],
        bump
    )]
    pub config: Account<'info, NetworkConfig>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct SetCompressionTree<'info> {
    #[account(
        mut,
        seeds = [b"config"],
        bump = config.bump,
        has_one = authority @ VaxchainError::UnauthorizedNetworkAuthority
    )]
    pub config: Account<'info, NetworkConfig>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct RotateNetworkAuthority<'info> {
    #[account(
        mut,
        seeds = [b"config"],
        bump = config.bump,
        has_one = authority @ VaxchainError::UnauthorizedNetworkAuthority
    )]
    pub config: Account<'info, NetworkConfig>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
#[instruction(hub_code: String)]
pub struct RegisterHub<'info> {
    #[account(
        mut,
        seeds = [b"config"],
        bump = config.bump,
        has_one = authority @ VaxchainError::UnauthorizedNetworkAuthority
    )]
    pub config: Account<'info, NetworkConfig>,
    #[account(
        init,
        payer = authority,
        space = 8 + HubAccount::MAX_SIZE,
        seeds = [b"hub", hub_code.as_bytes()],
        bump
    )]
    pub hub: Account<'info, HubAccount>,
    /// CHECK: This account is only used to record the hub authority pubkey during registration.
    /// No account data is read or written, and later instructions validate authority using the stored key.
    pub hub_authority: UncheckedAccount<'info>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(params: CreateBatchParams)]
pub struct CreateBatch<'info> {
    #[account(mut, seeds = [b"config"], bump = config.bump)]
    pub config: Account<'info, NetworkConfig>,
    #[account(seeds = [b"hub", hub.hub_code.as_bytes()], bump = hub.bump)]
    pub hub: Account<'info, HubAccount>,
    #[account(
        init,
        payer = authority,
        space = 8 + MedicineBatch::MAX_SIZE,
        seeds = [b"batch".as_ref(), params.batch_id_hash.as_ref()],
        bump
    )]
    pub batch: Account<'info, MedicineBatch>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct RecordIntake<'info> {
    #[account(seeds = [b"hub", hub.hub_code.as_bytes()], bump = hub.bump)]
    pub hub: Account<'info, HubAccount>,
    #[account(mut, seeds = [b"batch".as_ref(), batch.batch_id_hash.as_ref()], bump = batch.bump)]
    pub batch: Account<'info, MedicineBatch>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct InitiateTransfer<'info> {
    #[account(seeds = [b"hub", source_hub.hub_code.as_bytes()], bump = source_hub.bump)]
    pub source_hub: Account<'info, HubAccount>,
    #[account(seeds = [b"hub", destination_hub.hub_code.as_bytes()], bump = destination_hub.bump)]
    pub destination_hub: Account<'info, HubAccount>,
    #[account(mut, seeds = [b"batch".as_ref(), batch.batch_id_hash.as_ref()], bump = batch.bump)]
    pub batch: Account<'info, MedicineBatch>,
    #[account(
        init,
        payer = authority,
        space = 8 + CustodyTransfer::MAX_SIZE,
        seeds = [
            b"transfer".as_ref(),
            batch.batch_id_hash.as_ref(),
            batch.transfer_nonce.to_le_bytes().as_ref(),
        ],
        bump
    )]
    pub transfer: Account<'info, CustodyTransfer>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ReceiveTransfer<'info> {
    #[account(seeds = [b"hub", destination_hub.hub_code.as_bytes()], bump = destination_hub.bump)]
    pub destination_hub: Account<'info, HubAccount>,
    #[account(mut, seeds = [b"batch".as_ref(), batch.batch_id_hash.as_ref()], bump = batch.bump)]
    pub batch: Account<'info, MedicineBatch>,
    #[account(
        mut,
        seeds = [
            b"transfer".as_ref(),
            batch.batch_id_hash.as_ref(),
            transfer.nonce.to_le_bytes().as_ref(),
        ],
        bump = transfer.bump
    )]
    pub transfer: Account<'info, CustodyTransfer>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct RecordDispensation<'info> {
    #[account(seeds = [b"hub", hub.hub_code.as_bytes()], bump = hub.bump)]
    pub hub: Account<'info, HubAccount>,
    #[account(mut, seeds = [b"batch".as_ref(), batch.batch_id_hash.as_ref()], bump = batch.bump)]
    pub batch: Account<'info, MedicineBatch>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct ManageHubStatus<'info> {
    #[account(
        seeds = [b"config"],
        bump = config.bump,
        has_one = authority @ VaxchainError::UnauthorizedNetworkAuthority
    )]
    pub config: Account<'info, NetworkConfig>,
    #[account(mut, seeds = [b"hub", hub.hub_code.as_bytes()], bump = hub.bump)]
    pub hub: Account<'info, HubAccount>,
    pub authority: Signer<'info>,
}

#[account]
pub struct NetworkConfig {
    pub authority: Pubkey,
    pub compression_tree: Pubkey,
    pub version: u8,
    pub hub_count: u32,
    pub batch_count: u64,
    pub bump: u8,
}

impl NetworkConfig {
    pub const MAX_SIZE: usize = 32 + 32 + 1 + 4 + 8 + 1;
}

#[account]
pub struct HubAccount {
    pub authority: Pubkey,
    pub hub_code: String,
    pub hub_label_hash: [u8; 32],
    pub is_active: bool,
    pub bump: u8,
}

impl HubAccount {
    pub const MAX_SIZE: usize = 32 + 4 + HUB_CODE_MAX_LEN + 32 + 1 + 1;
}

#[account]
pub struct MedicineBatch {
    pub batch_id_hash: [u8; 32],
    pub batch_code: String,
    pub medicine_code: String,
    pub document_hash: [u8; 32],
    pub metadata_hash: [u8; 32],
    pub current_hub: Pubkey,
    pub created_by: Pubkey,
    pub total_units: u64,
    pub remaining_units: u64,
    pub dispensed_units: u64,
    pub transfer_nonce: u64,
    pub status: u8,
    pub created_at: i64,
    pub updated_at: i64,
    pub bump: u8,
}

impl MedicineBatch {
    pub const MAX_SIZE: usize = 32 + (4 + BATCH_CODE_MAX_LEN) + (4 + MEDICINE_CODE_MAX_LEN)
        + 32 + 32 + 32 + 32 + 8 + 8 + 8 + 8 + 1 + 8 + 8 + 1;
}

#[account]
pub struct CustodyTransfer {
    pub batch: Pubkey,
    pub batch_id_hash: [u8; 32],
    pub from_hub: Pubkey,
    pub to_hub: Pubkey,
    pub quantity: u64,
    pub status: u8,
    pub reference_hash: [u8; 32],
    pub initiated_by: Pubkey,
    pub received_by: Pubkey,
    pub initiated_at: i64,
    pub received_at: i64,
    pub nonce: u64,
    pub bump: u8,
}

impl CustodyTransfer {
    pub const MAX_SIZE: usize = 32 + 32 + 32 + 32 + 8 + 1 + 32 + 32 + 32 + 8 + 8 + 8 + 1;
}

#[event]
pub struct NetworkInitialized {
    pub authority: Pubkey,
    pub compression_tree: Pubkey,
}

#[event]
pub struct CompressionTreeUpdated {
    pub authority: Pubkey,
    pub compression_tree: Pubkey,
}

#[event]
pub struct NetworkAuthorityRotated {
    pub previous_authority: Pubkey,
    pub new_authority: Pubkey,
}

#[event]
pub struct HubRegistered {
    pub hub: Pubkey,
    pub authority: Pubkey,
    pub hub_code: String,
}

#[event]
pub struct HubDeactivated {
    pub hub: Pubkey,
    pub authority: Pubkey,
    pub hub_code: String,
}

#[event]
pub struct HubReactivated {
    pub hub: Pubkey,
    pub authority: Pubkey,
    pub hub_code: String,
}

#[event]
pub struct BatchCreated {
    pub batch: Pubkey,
    pub batch_id_hash: [u8; 32],
    pub current_hub: Pubkey,
    pub total_units: u64,
    pub document_hash: [u8; 32],
}

#[event]
pub struct IntakeRecorded {
    pub batch: Pubkey,
    pub hub: Pubkey,
    pub reference_hash: [u8; 32],
}

#[event]
pub struct TransferInitiated {
    pub transfer: Pubkey,
    pub batch: Pubkey,
    pub from_hub: Pubkey,
    pub to_hub: Pubkey,
    pub quantity: u64,
    pub nonce: u64,
}

#[event]
pub struct TransferReceived {
    pub transfer: Pubkey,
    pub batch: Pubkey,
    pub destination_hub: Pubkey,
    pub quantity: u64,
    pub nonce: u64,
}

#[event]
pub struct DispensationRecorded {
    pub batch: Pubkey,
    pub hub: Pubkey,
    pub dispensed_units: u64,
    pub remaining_units: u64,
    pub reference_hash: [u8; 32],
}

#[error_code]
pub enum VaxchainError {
    #[msg("Only the network authority can perform this action.")]
    UnauthorizedNetworkAuthority,
    #[msg("Only the hub authority can perform this action.")]
    UnauthorizedHubAuthority,
    #[msg("Compression tree pubkey cannot be the default address.")]
    InvalidCompressionTree,
    #[msg("Authority pubkey cannot be the default address.")]
    InvalidAuthorityKey,
    #[msg("Hub code cannot be empty.")]
    EmptyHubCode,
    #[msg("Batch code cannot be empty.")]
    EmptyBatchCode,
    #[msg("Medicine code cannot be empty.")]
    EmptyMedicineCode,
    #[msg("Hub code exceeds the supported maximum length.")]
    HubCodeTooLong,
    #[msg("Batch code exceeds the supported maximum length.")]
    BatchCodeTooLong,
    #[msg("Medicine code exceeds the supported maximum length.")]
    MedicineCodeTooLong,
    #[msg("Quantity must be greater than zero.")]
    InvalidQuantity,
    #[msg("Hub is inactive.")]
    HubInactive,
    #[msg("Hub is already active.")]
    HubAlreadyActive,
    #[msg("Hub is already inactive.")]
    HubAlreadyInactive,
    #[msg("Batch is not in the expected lifecycle state for this action.")]
    InvalidBatchState,
    #[msg("The batch is not currently assigned to this hub.")]
    InvalidCurrentHub,
    #[msg("Source and destination hubs must differ.")]
    DestinationHubMustDiffer,
    #[msg("No remaining units are available for transfer.")]
    NothingToTransfer,
    #[msg("The transfer has already been received.")]
    TransferAlreadySettled,
    #[msg("Transfer record does not match the provided batch.")]
    TransferBatchMismatch,
    #[msg("Transfer destination does not match the provided hub.")]
    WrongDestinationHub,
    #[msg("Requested quantity exceeds remaining units.")]
    InsufficientUnits,
    #[msg("Arithmetic overflow detected.")]
    MathOverflow,
}
