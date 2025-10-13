import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useNavigate } from 'react-router-dom';
import { Bot, Mail, Calendar, MessageSquare, LogOut, ArrowLeft, Trash2, Key, Lock } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '@/services/api';
import { deleteLocalEmotionData } from '@/services/emotionStorage';

const Profile = () => {
  const { user, isGuest, guestMessageCount, logout } = useAuth();
  const navigate = useNavigate();
  
  const [isUpdating, setIsUpdating] = useState(false);
  const [updateEmail, setUpdateEmail] = useState('');
  const [updatePassword, setUpdatePassword] = useState('');
  const [updateSecretKey, setUpdateSecretKey] = useState('');
  const [deleteConfirmation, setDeleteConfirmation] = useState('');

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleUpdateProfile = async () => {
    if (!updateEmail && !updatePassword && !updateSecretKey) {
      toast.error('Please fill in at least one field to update');
      return;
    }

    setIsUpdating(true);
    try {
      const updateData: any = {};
      if (updateEmail) updateData.email = updateEmail;
      if (updatePassword) updateData.password = updatePassword;
      if (updateSecretKey) updateData.secret_key = updateSecretKey;

      const response = await api.updateProfile(updateData);
      
      if (response.error) {
        toast.error(response.error);
      } else {
        toast.success('Profile updated successfully');
        setUpdateEmail('');
        setUpdatePassword('');
        setUpdateSecretKey('');
      }
    } catch (error) {
      toast.error('Failed to update profile');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDeleteEmotionData = async () => {
    if (deleteConfirmation !== 'DELETE-FOREVER') {
      toast.error('Please type DELETE-FOREVER to confirm');
      return;
    }

    try {
      deleteLocalEmotionData();
      await api.deleteEmotionData();
      toast.success('Emotion data deleted successfully');
      setDeleteConfirmation('');
    } catch (error) {
      toast.error('Failed to acknowledge deletion');
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col relative overflow-hidden">
      {/* Animated background */}
      <div className="fixed inset-0 bg-gradient-to-br from-primary/5 via-background to-accent/5 pointer-events-none" />
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent pointer-events-none" />

      <div className="relative flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-2xl">
          {/* Back Button */}
          <Button
            variant="ghost"
            className="mb-6"
            onClick={() => navigate('/')}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Chat
          </Button>

          <div className="glass-effect rounded-2xl border border-border/50 p-8 shadow-2xl">
            {/* Profile Header */}
            <div className="flex flex-col items-center mb-8">
              <div className="w-20 h-20 rounded-2xl bg-primary/20 border border-primary/50 flex items-center justify-center glow-primary mb-4">
                <Bot className="w-10 h-10 text-primary" />
              </div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                {isGuest ? 'Guest Profile' : 'Your Profile'}
              </h1>
              <p className="text-sm text-muted-foreground mt-2">
                {isGuest ? 'Limited access mode' : 'Full access account'}
              </p>
            </div>

            {/* Profile Info */}
            <div className="space-y-6">
              {isGuest ? (
                <>
                  <div className="flex items-start gap-4 p-4 rounded-xl bg-background/50 border border-border/50">
                    <MessageSquare className="w-5 h-5 text-primary mt-0.5" />
                    <div className="flex-1">
                      <h3 className="font-semibold text-foreground mb-1">Messages Used</h3>
                      <p className="text-sm text-muted-foreground">
                        {guestMessageCount} / 20 messages
                      </p>
                      <div className="w-full bg-border/30 rounded-full h-2 mt-2">
                        <div
                          className="bg-primary h-2 rounded-full transition-all"
                          style={{ width: `${(guestMessageCount / 20) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-accent/10 border border-accent/30">
                    <p className="text-sm text-foreground/80">
                      Create an account to get unlimited access and save your chat history across devices.
                    </p>
                    <Button
                      className="w-full mt-4"
                      onClick={() => navigate('/register')}
                    >
                      Create Account
                    </Button>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex items-start gap-4 p-4 rounded-xl bg-background/50 border border-border/50">
                    <Mail className="w-5 h-5 text-primary mt-0.5" />
                    <div className="flex-1">
                      <h3 className="font-semibold text-foreground mb-1">Email</h3>
                      <p className="text-sm text-muted-foreground">{user?.email}</p>
                    </div>
                  </div>

                  <div className="flex items-start gap-4 p-4 rounded-xl bg-background/50 border border-border/50">
                    <Calendar className="w-5 h-5 text-primary mt-0.5" />
                    <div className="flex-1">
                      <h3 className="font-semibold text-foreground mb-1">Member Since</h3>
                      <p className="text-sm text-muted-foreground">
                        {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-4 p-4 rounded-xl bg-background/50 border border-border/50">
                    <MessageSquare className="w-5 h-5 text-primary mt-0.5" />
                    <div className="flex-1">
                      <h3 className="font-semibold text-foreground mb-1">Access Level</h3>
                      <p className="text-sm text-muted-foreground">Unlimited messages</p>
                    </div>
                  </div>

                  {/* Update Profile Section */}
                  <div className="p-4 rounded-xl bg-background/50 border border-border/50">
                    <h3 className="font-semibold text-foreground mb-4">Update Profile</h3>
                    <div className="space-y-3">
                      <div>
                        <Label htmlFor="updateEmail" className="text-foreground/80">New Email</Label>
                        <div className="relative mt-1">
                          <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                          <Input
                            id="updateEmail"
                            type="email"
                            placeholder="new@example.com"
                            value={updateEmail}
                            onChange={(e) => setUpdateEmail(e.target.value)}
                            className="pl-10 bg-background/50 border-border/50"
                          />
                        </div>
                      </div>

                      <div>
                        <Label htmlFor="updatePassword" className="text-foreground/80">New Password</Label>
                        <div className="relative mt-1">
                          <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                          <Input
                            id="updatePassword"
                            type="password"
                            placeholder="••••••••"
                            value={updatePassword}
                            onChange={(e) => setUpdatePassword(e.target.value)}
                            className="pl-10 bg-background/50 border-border/50"
                          />
                        </div>
                      </div>

                      <div>
                        <Label htmlFor="updateSecretKey" className="text-foreground/80">New Secret Key</Label>
                        <div className="relative mt-1">
                          <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                          <Input
                            id="updateSecretKey"
                            type="password"
                            placeholder="New secret key"
                            value={updateSecretKey}
                            onChange={(e) => setUpdateSecretKey(e.target.value)}
                            className="pl-10 bg-background/50 border-border/50"
                          />
                        </div>
                      </div>

                      <Button
                        onClick={handleUpdateProfile}
                        disabled={isUpdating}
                        className="w-full"
                      >
                        {isUpdating ? 'Updating...' : 'Update Profile'}
                      </Button>
                    </div>
                  </div>

                  {/* Delete Emotion Data Section */}
                  <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/30">
                    <h3 className="font-semibold text-foreground mb-2 flex items-center gap-2">
                      <Trash2 className="w-4 h-4" />
                      Delete Local Emotion Data
                    </h3>
                    <p className="text-sm text-muted-foreground mb-3">
                      This will permanently delete all emotion data stored locally on this device.
                      Type <strong>DELETE-FOREVER</strong> to confirm.
                    </p>
                    <div className="space-y-2">
                      <Input
                        type="text"
                        placeholder="Type DELETE-FOREVER"
                        value={deleteConfirmation}
                        onChange={(e) => setDeleteConfirmation(e.target.value)}
                        className="bg-background/50 border-border/50"
                      />
                      <Button
                        variant="destructive"
                        onClick={handleDeleteEmotionData}
                        disabled={deleteConfirmation !== 'DELETE-FOREVER'}
                        className="w-full"
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Delete Emotion Data
                      </Button>
                    </div>
                  </div>
                </>
              )}

              {/* Privacy Notice */}
              <div className="p-4 rounded-xl bg-primary/10 border border-primary/30">
                <h3 className="font-semibold text-foreground mb-2">🔒 Privacy Notice</h3>
                <p className="text-sm text-muted-foreground">
                  All emotion data is stored locally on your device and never uploaded to any server.
                  Your privacy is our top priority.
                </p>
              </div>

              {/* Logout Button */}
              <Button
                variant="outline"
                className="w-full"
                onClick={handleLogout}
              >
                <LogOut className="w-4 h-4 mr-2" />
                {isGuest ? 'Exit Guest Mode' : 'Sign Out'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
