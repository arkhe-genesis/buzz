use safe_core_identity::ArkheDid;

#[derive(Debug, Clone)]
pub struct CapabilityToken {
    pub issuer: ArkheDid,
    pub subject: ArkheDid,
    pub permissions: Vec<String>,
    pub expires_in: std::time::Duration,
}

impl CapabilityToken {
    pub fn issue(
        issuer: ArkheDid,
        subject: ArkheDid,
        permissions: Vec<String>,
        expires_in: std::time::Duration,
        _key: &[u8],
    ) -> Result<Self, ()> {
        Ok(Self {
            issuer,
            subject,
            permissions,
            expires_in,
        })
    }
}
